import json
import time
from typing import Dict, Any, Optional
from enum import Enum

class MessageType(Enum):
    HANDSHAKE = "handshake"
    TEXT = "text"
    ACK = "ack"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

class MessageProtocol:
    VERSION = "1.0"
    
    @staticmethod
    def create_message(msg_type: MessageType, sender_id: str, 
                      recipient_id: str = None, content: Any = None, 
                      message_id: str = None) -> Dict[str, Any]:
        """Create a message following the protocol"""
        import uuid
        
        message = {
            "version": MessageProtocol.VERSION,
            "type": msg_type.value,
            "sender_id": sender_id,
            "message_id": message_id or str(uuid.uuid4()),
            "timestamp": time.time()
        }
        
        if recipient_id:
            message["recipient_id"] = recipient_id
            
        if content is not None:
            message["content"] = content
            
        return message
    
    @staticmethod
    def encode_message(message: Dict[str, Any]) -> bytes:
        """Encode message to bytes"""
        return json.dumps(message).encode('utf-8')
    
    @staticmethod
    def decode_message(data: bytes) -> Optional[Dict[str, Any]]:
        """Decode message from bytes"""
        try:
            message = json.loads(data.decode('utf-8'))
            # Validate required fields
            required = ["version", "type", "sender_id", "message_id", "timestamp"]
            if all(field in message for field in required):
                return message
        except Exception as e:
            pass
        return None
    
    @staticmethod
    def create_handshake(peer_id: str, peer_info: Dict[str, Any]) -> bytes:
        """Create handshake message"""
        message = MessageProtocol.create_message(
            MessageType.HANDSHAKE,
            peer_id,
            content=peer_info
        )
        return MessageProtocol.encode_message(message)
    
    @staticmethod
    def create_text_message(sender_id: str, recipient_id: str, text: str) -> bytes:
        """Create text message"""
        message = MessageProtocol.create_message(
            MessageType.TEXT,
            sender_id,
            recipient_id,
            content={"text": text}
        )
        return MessageProtocol.encode_message(message)