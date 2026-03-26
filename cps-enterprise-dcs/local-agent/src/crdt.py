"""
CRDT (Conflict-free Replicated Data Types) Implementation
=========================================================
Mathematically proven data structures for distributed state.

These structures guarantee Strong Eventual Consistency (SEC):
- If the same set of updates is applied to replicas, they converge
- No coordination required during updates
- Perfect for offline-first retail operations

Reference: Shapiro et al. "A comprehensive study of Convergent and 
Commutative Replicated Data Types"
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, Set, TypeVar, Any
from copy import deepcopy
import hashlib

T = TypeVar('T')


class CRDT(ABC, Generic[T]):
    """Base class for all CRDT implementations."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._version = 0
    
    @abstractmethod
    def merge(self, other: T) -> T:
        """Merge another replica into this one."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> T:
        """Deserialize from dictionary."""
        pass
    
    @property
    def version(self) -> int:
        return self._version
    
    def _increment_version(self):
        self._version += 1


@dataclass
class GCounter(CRDT['GCounter']):
    """
    Grow-only Counter CRDT
    ======================
    Only supports increment operations.
    
    Merge: Take maximum of each node's counter
    Use case: Total sales count, visitor counters
    
    Example:
        >>> counter = GCounter("branch_001")
        >>> counter.increment(5)
        >>> counter.value
        5
    """
    
    node_id: str
    _increments: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(self.node_id)
        if self.node_id not in self._increments:
            self._increments[self.node_id] = 0
    
    def increment(self, amount: int = 1) -> None:
        """Increment this node's counter."""
        if amount < 0:
            raise ValueError("GCounter only supports positive increments")
        self._increments[self.node_id] = self._increments.get(self.node_id, 0) + amount
        self._increment_version()
    
    @property
    def value(self) -> int:
        """Total value across all nodes."""
        return sum(self._increments.values())
    
    def merge(self, other: 'GCounter') -> 'GCounter':
        """
        Merge another GCounter into this one.
        Takes maximum value for each node.
        """
        merged = GCounter(self.node_id)
        all_nodes = set(self._increments.keys()) | set(other._increments.keys())
        
        for node in all_nodes:
            merged._increments[node] = max(
                self._increments.get(node, 0),
                other._increments.get(node, 0)
            )
        
        merged._version = max(self._version, other._version) + 1
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "GCounter",
            "node_id": self.node_id,
            "increments": self._increments.copy(),
            "version": self._version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GCounter':
        counter = cls(node_id=data["node_id"])
        counter._increments = data.get("increments", {}).copy()
        counter._version = data.get("version", 0)
        return counter


@dataclass
class PNCounter(CRDT['PNCounter']):
    """
    Positive-Negative Counter CRDT
    ==============================
    Supports both increment and decrement operations.
    
    Merge: Take maximum of positive and negative counters separately
    Use case: Inventory tracking, account balances
    
    Example:
        >>> counter = PNCounter("branch_001")
        >>> counter.increment(100)  # Receive 100 items
        >>> counter.decrement(30)   # Sell 30 items
        >>> counter.value
        70
    """
    
    node_id: str
    _increments: Dict[str, int] = field(default_factory=dict)
    _decrements: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(self.node_id)
        if self.node_id not in self._increments:
            self._increments[self.node_id] = 0
        if self.node_id not in self._decrements:
            self._decrements[self.node_id] = 0
    
    def increment(self, amount: int = 1) -> None:
        """Increment (add to positive counter)."""
        if amount < 0:
            raise ValueError("Use decrement() for negative values")
        self._increments[self.node_id] = self._increments.get(self.node_id, 0) + amount
        self._increment_version()
    
    def decrement(self, amount: int = 1) -> None:
        """Decrement (add to negative counter)."""
        if amount < 0:
            raise ValueError("Use increment() for positive values")
        self._decrements[self.node_id] = self._decrements.get(self.node_id, 0) + amount
        self._increment_version()
    
    @property
    def value(self) -> int:
        """Net value: positive - negative."""
        pos = sum(self._increments.values())
        neg = sum(self._decrements.values())
        return pos - neg
    
    @property
    def positive(self) -> int:
        """Total positive increments."""
        return sum(self._increments.values())
    
    @property
    def negative(self) -> int:
        """Total negative increments."""
        return sum(self._decrements.values())
    
    def merge(self, other: 'PNCounter') -> 'PNCounter':
        """Merge another PNCounter into this one."""
        merged = PNCounter(self.node_id)
        all_nodes = set(self._increments.keys()) | set(other._increments.keys())
        
        for node in all_nodes:
            merged._increments[node] = max(
                self._increments.get(node, 0),
                other._increments.get(node, 0)
            )
            merged._decrements[node] = max(
                self._decrements.get(node, 0),
                other._decrements.get(node, 0)
            )
        
        merged._version = max(self._version, other._version) + 1
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "PNCounter",
            "node_id": self.node_id,
            "increments": self._increments.copy(),
            "decrements": self._decrements.copy(),
            "version": self._version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PNCounter':
        counter = cls(node_id=data["node_id"])
        counter._increments = data.get("increments", {}).copy()
        counter._decrements = data.get("decrements", {}).copy()
        counter._version = data.get("version", 0)
        return counter


@dataclass
class ORSetElement:
    """Element in an Observed-Remove Set."""
    element_id: str
    value: str
    is_removed: bool = False
    added_at: Optional[str] = None
    removed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "value": self.value,
            "is_removed": self.is_removed,
            "added_at": self.added_at,
            "removed_at": self.removed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ORSetElement':
        return cls(
            element_id=data["element_id"],
            value=data["value"],
            is_removed=data.get("is_removed", False),
            added_at=data.get("added_at"),
            removed_at=data.get("removed_at")
        )


@dataclass
class ORSet(CRDT['ORSet']):
    """
    Observed-Remove Set CRDT
    ========================
    Supports add and remove operations with conflict resolution.
    
    Key insight: Each addition gets a unique ID. Removal removes specific IDs.
    If add and remove happen concurrently, both are preserved.
    
    Merge: Union of all non-removed elements
    Use case: Product catalogs, active promotions, user sessions
    
    Example:
        >>> orset = ORSet("branch_001")
        >>> orset.add("product_A")
        >>> orset.add("product_B")
        >>> orset.remove("product_A")
        >>> list(orset.elements)
        ["product_B"]
    """
    
    node_id: str
    _elements: Dict[str, ORSetElement] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(self.node_id)
    
    def add(self, value: str, element_id: Optional[str] = None) -> str:
        """
        Add an element to the set.
        Returns the unique element ID.
        """
        import uuid
        if element_id is None:
            element_id = str(uuid.uuid4())
        
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        
        element = ORSetElement(
            element_id=element_id,
            value=value,
            is_removed=False,
            added_at=timestamp
        )
        
        self._elements[element_id] = element
        self._increment_version()
        return element_id
    
    def remove(self, value: str) -> List[str]:
        """
        Remove all occurrences of a value.
        Returns list of removed element IDs.
        """
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        removed_ids = []
        
        for element_id, element in self._elements.items():
            if element.value == value and not element.is_removed:
                element.is_removed = True
                element.removed_at = timestamp
                removed_ids.append(element_id)
        
        if removed_ids:
            self._increment_version()
        
        return removed_ids
    
    def remove_by_id(self, element_id: str) -> bool:
        """Remove a specific element by its ID."""
        if element_id in self._elements:
            from datetime import datetime
            element = self._elements[element_id]
            if not element.is_removed:
                element.is_removed = True
                element.removed_at = datetime.utcnow().isoformat()
                self._increment_version()
                return True
        return False
    
    @property
    def elements(self) -> Set[str]:
        """Get all active (non-removed) elements."""
        return {
            e.value for e in self._elements.values()
            if not e.is_removed
        }
    
    @property
    def removed_elements(self) -> Set[str]:
        """Get all removed elements."""
        return {
            e.value for e in self._elements.values()
            if e.is_removed
        }
    
    def contains(self, value: str) -> bool:
        """Check if value exists in active elements."""
        return value in self.elements
    
    def merge(self, other: 'ORSet') -> 'ORSet':
        """
        Merge another ORSet into this one.
        Takes union of all elements, preserving removal status.
        """
        merged = ORSet(self.node_id)
        all_ids = set(self._elements.keys()) | set(other._elements.keys())
        
        for element_id in all_ids:
            self_elem = self._elements.get(element_id)
            other_elem = other._elements.get(element_id)
            
            if self_elem and other_elem:
                # Both have the element - merge removal status
                merged_elem = ORSetElement(
                    element_id=element_id,
                    value=self_elem.value,
                    is_removed=self_elem.is_removed or other_elem.is_removed,
                    added_at=self_elem.added_at or other_elem.added_at,
                    removed_at=self_elem.removed_at or other_elem.removed_at
                )
            elif self_elem:
                merged_elem = ORSetElement.from_dict(self_elem.to_dict())
            else:
                merged_elem = ORSetElement.from_dict(other_elem.to_dict())
            
            merged._elements[element_id] = merged_elem
        
        merged._version = max(self._version, other._version) + 1
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ORSet",
            "node_id": self.node_id,
            "elements": {k: v.to_dict() for k, v in self._elements.items()},
            "version": self._version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ORSet':
        orset = cls(node_id=data["node_id"])
        orset._elements = {
            k: ORSetElement.from_dict(v)
            for k, v in data.get("elements", {}).items()
        }
        orset._version = data.get("version", 0)
        return orset


@dataclass
class LWWRegister(CRDT['LWWRegister']):
    """
    Last-Write-Wins Register CRDT
    =============================
    Single value with timestamp-based conflict resolution.
    
    Merge: Take value with highest timestamp
    Use case: Configuration values, prices, settings
    
    Example:
        >>> reg = LWWRegister("branch_001")
        >>> reg.set("price_100")
        >>> reg.value
        "price_100"
    """
    
    node_id: str
    _value: str = ""
    _timestamp: str = ""
    
    def __post_init__(self):
        super().__init__(self.node_id)
    
    def set(self, value: str, timestamp: Optional[str] = None) -> None:
        """Set the register value."""
        from datetime import datetime
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        # Only update if new timestamp is greater
        if timestamp >= self._timestamp:
            self._value = value
            self._timestamp = timestamp
            self._increment_version()
    
    @property
    def value(self) -> str:
        """Get the register value."""
        return self._value
    
    @property
    def timestamp(self) -> str:
        """Get the timestamp of last update."""
        return self._timestamp
    
    def merge(self, other: 'LWWRegister') -> 'LWWRegister':
        """Merge another LWWRegister - last write wins."""
        merged = LWWRegister(self.node_id)
        
        if self._timestamp >= other._timestamp:
            merged._value = self._value
            merged._timestamp = self._timestamp
        else:
            merged._value = other._value
            merged._timestamp = other._timestamp
        
        merged._version = max(self._version, other._version) + 1
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "LWWRegister",
            "node_id": self.node_id,
            "value": self._value,
            "timestamp": self._timestamp,
            "version": self._version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LWWRegister':
        reg = cls(node_id=data["node_id"])
        reg._value = data.get("value", "")
        reg._timestamp = data.get("timestamp", "")
        reg._version = data.get("version", 0)
        return reg


class CRDTManager:
    """
    Central manager for all CRDT instances in a branch.
    Handles serialization, persistence, and synchronization.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._crdts: Dict[str, CRDT] = {}
        self._crdt_types: Dict[str, str] = {}
    
    def create_counter(self, crdt_id: str, counter_type: str = "PN") -> CRDT:
        """Create a new counter CRDT."""
        if counter_type == "G":
            counter = GCounter(self.node_id)
        else:
            counter = PNCounter(self.node_id)
        
        self._crdts[crdt_id] = counter
        self._crdt_types[crdt_id] = counter_type
        return counter
    
    def create_orset(self, crdt_id: str) -> ORSet:
        """Create a new ORSet CRDT."""
        orset = ORSet(self.node_id)
        self._crdts[crdt_id] = orset
        self._crdt_types[crdt_id] = "ORSet"
        return orset
    
    def create_lww_register(self, crdt_id: str) -> LWWRegister:
        """Create a new LWWRegister CRDT."""
        reg = LWWRegister(self.node_id)
        self._crdts[crdt_id] = reg
        self._crdt_types[crdt_id] = "LWWRegister"
        return reg
    
    def get(self, crdt_id: str) -> Optional[CRDT]:
        """Get a CRDT by ID."""
        return self._crdts.get(crdt_id)
    
    def merge(self, crdt_id: str, other: CRDT) -> CRDT:
        """Merge another replica into a local CRDT."""
        local = self._crdts.get(crdt_id)
        if local is None:
            # Clone the other CRDT with our node_id
            cloned = other.__class__.from_dict(other.to_dict())
            cloned.node_id = self.node_id
            self._crdts[crdt_id] = cloned
            return cloned
        
        merged = local.merge(other)
        self._crdts[crdt_id] = merged
        return merged
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all CRDT states for synchronization."""
        return {
            crdt_id: crdt.to_dict()
            for crdt_id, crdt in self._crdts.items()
        }
    
    def load_states(self, states: Dict[str, Dict[str, Any]]) -> None:
        """Load CRDT states from synchronization."""
        crdt_classes = {
            "GCounter": GCounter,
            "PNCounter": PNCounter,
            "ORSet": ORSet,
            "LWWRegister": LWWRegister
        }
        
        for crdt_id, state in states.items():
            crdt_type = state.get("type")
            if crdt_type in crdt_classes:
                self._crdts[crdt_id] = crdt_classes[crdt_type].from_dict(state)
