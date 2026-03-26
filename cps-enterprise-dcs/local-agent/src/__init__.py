"""
CP'S Enterprise DCS - Local Agent
=================================
The sovereign edge computing agent for retail branch operations.

This agent operates independently, ensuring business continuity
even during complete network isolation.

Author: Ahmed Hajjaj - Full-Spectrum Architect
"""

__version__ = "4.0.0"
__author__ = "Ahmed Hajjaj"
__license__ = "Proprietary"

from .agent import LocalAgent
from .crdt import PNCounter, GCounter, ORSet, LWWRegister
from .event_store import EventStore, SQLiteEventStore
from .security import SovereignPayload, CryptoManager

__all__ = [
    "LocalAgent",
    "PNCounter",
    "GCounter", 
    "ORSet",
    "LWWRegister",
    "EventStore",
    "SQLiteEventStore",
    "SovereignPayload",
    "CryptoManager",
]
