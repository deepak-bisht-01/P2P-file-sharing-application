from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

@dataclass
class Peer:
    """Represents a peer in the network"""
    peer_id: str
    address: str
    port: int
    public_key: Optional[str] = None
    last_seen: datetime = field(default_factory=datetime.now)
    status: str = "online"  # online, offline, unknown
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "port": self.port,
            "public_key": self.public_key,
            "last_seen": self.last_seen.isoformat(),
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Peer':
        data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)

@dataclass
class Message:
    """Represents a message in the system"""
    message_id: str
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, sent, delivered, failed
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "retry_count": self.retry_count
        }
    
    def to_wire_format(self) -> Dict[str, Any]:
        """Convert to format for network transmission"""
        return {
            "version": "1.0",
            "type": self.message_type,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp.timestamp(),
            "content": self.content
        }