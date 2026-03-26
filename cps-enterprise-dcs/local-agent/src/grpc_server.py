"""
gRPC Server for Local Agent
===========================
Exposes Local Agent functionality via gRPC.

Services:
- AccountingSwarmProtocol: Event broadcasting and sync
- QueryProtocol: Read model queries
- AgentCommunication: Inter-agent messaging
"""

from __future__ import annotations

import asyncio
from concurrent import futures
from typing import AsyncIterator
import grpc
from datetime import datetime

# Import generated protobuf code (will be generated from .proto)
# For now, we'll create stub implementations

from .agent import LocalAgent, AgentConfig
from .event_store import StoredEvent, EventMetadata


class AccountingSwarmServicer:
    """gRPC servicer for AccountingSwarmProtocol."""
    
    def __init__(self, agent: LocalAgent):
        self.agent = agent
    
    async def BroadcastFinancialEvent(self, request, context):
        """Handle single event broadcast."""
        try:
            # Parse the event from request
            event_type = request.event_type
            payload = request.payload
            
            # Create metadata
            metadata = EventMetadata(
                correlation_id=request.correlation_id,
                agent_id=request.agent_id
            )
            
            # Append to event store
            stream_id = f"{self.agent.config.branch_id}:incoming"
            event = await self.agent.event_store.append(
                stream_id=stream_id,
                event_type=event_type,
                payload=payload,
                metadata=metadata
            )
            
            # Build response
            return {
                "success": True,
                "message": "Event recorded",
                "receipt_hash": event.event_hash,
                "is_duplicate": False
            }
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return {
                "success": False,
                "message": str(e)
            }
    
    async def SubscribeEvents(self, request, context):
        """Stream events to subscriber."""
        branch_id = request.branch_id
        event_types = list(request.event_types)
        
        # Subscribe to events
        from .event_store import EventStoreSubscription
        subscription = EventStoreSubscription(
            self.agent.event_store,
            event_types=event_types if event_types else None
        )
        
        # Create async generator
        async for event in self._event_generator(subscription):
            yield self._stored_event_to_proto(event)
    
    async def _event_generator(self, subscription):
        """Generate events from subscription."""
        queue = asyncio.Queue()
        
        def handler(event: StoredEvent):
            queue.put_nowait(event)
        
        subscription.on_event(handler)
        
        # Start subscription in background
        asyncio.create_task(subscription.start())
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            subscription.stop()
    
    def _stored_event_to_proto(self, event: StoredEvent):
        """Convert StoredEvent to protobuf message."""
        return {
            "event_id": event.event_id,
            "stream_id": event.stream_id,
            "version": event.version,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at.isoformat()
        }
    
    async def RequestReconciliation(self, request, context):
        """Handle reconciliation request."""
        # TODO: Implement full reconciliation logic
        return {
            "is_balanced": True,
            "actual_balance": 0.0,
            "discrepancy_event_ids": [],
            "validation_signature": ""
        }
    
    async def SwarmEventExchange(self, request_iterator, context):
        """Bidirectional event exchange."""
        # Handle incoming events
        async for request in request_iterator:
            # Process event
            pass
        
        # Yield outgoing events
        while True:
            # TODO: Get events from queue
            await asyncio.sleep(1)
            yield {
                "event_id": "",
                "event_type": "HEARTBEAT"
            }


class QueryServicer:
    """gRPC servicer for QueryProtocol."""
    
    def __init__(self, agent: LocalAgent):
        self.agent = agent
    
    async def GetBranchSummary(self, request, context):
        """Get branch summary."""
        summary = await self.agent.get_branch_summary()
        return {
            "branch_id": summary["branch_id"],
            "today_sales": summary["today_sales"],
            "today_transactions": 0,  # TODO: Calculate
            "current_balance": 0.0,  # TODO: Calculate
            "active_sessions": 0,  # TODO: Track
            "alerts": []
        }
    
    async def GetInventoryStatus(self, request, context):
        """Get inventory status."""
        product_id = request.product_id
        quantity = self.agent.get_inventory_level(product_id)
        
        return {
            "product_id": product_id,
            "branch_id": self.agent.config.branch_id,
            "current_quantity": quantity,
            "reserved_quantity": 0,
            "available_quantity": quantity,
            "reorder_point": 10,
            "is_low_stock": quantity < 10
        }
    
    async def GetSalesReport(self, request, context):
        """Get sales report."""
        # TODO: Implement sales report generation
        return {
            "entries": [],
            "total_sales": self.agent.get_daily_sales(),
            "total_transactions": 0,
            "average_transaction": 0.0
        }
    
    async def SubscribeDashboard(self, request, context):
        """Stream dashboard updates."""
        while True:
            summary = await self.agent.get_branch_summary()
            
            yield {
                "metric_name": "today_sales",
                "value": summary["today_sales"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await asyncio.sleep(request.update_interval_ms / 1000.0)


class LocalAgentGRPCServer:
    """gRPC server for the local agent."""
    
    def __init__(self, agent: LocalAgent, port: int = 50051):
        self.agent = agent
        self.port = port
        self.server = None
    
    async def start(self):
        """Start the gRPC server."""
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Add servicers
        # TODO: Register services with generated protobuf code
        
        self.server.add_insecure_port(f"[::]:{self.port}")
        await self.server.start()
        
        print(f"gRPC server started on port {self.port}")
    
    async def stop(self):
        """Stop the gRPC server."""
        if self.server:
            await self.server.stop(5)
            print("gRPC server stopped")
    
    async def serve_forever(self):
        """Run server until interrupted."""
        await self.server.wait_for_termination()
