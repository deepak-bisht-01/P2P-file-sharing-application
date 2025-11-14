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
    FILE_MANIFEST = "file_manifest"
    FILE_CHUNK_REQUEST = "file_chunk_request"
    FILE_CHUNK = "file_chunk"
    FILE_COMPLETE = "file_complete"
    FILE_AVAILABILITY = "file_availability"

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
        """Encode message to bytes with length prefix for reliable framing"""
        json_bytes = json.dumps(message).encode('utf-8')
        # Prefix with length (4 bytes, big-endian) so we know exactly how many bytes to read
        length = len(json_bytes)
        return length.to_bytes(4, byteorder='big') + json_bytes
    
    @staticmethod
    def decode_message(data: bytes) -> Optional[Dict[str, Any]]:
        """Decode message from bytes (expects raw JSON, not length-prefixed)"""
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

    @staticmethod
    def create_file_manifest(sender_id: str, manifest: Dict[str, Any]) -> bytes:
        message = MessageProtocol.create_message(
            MessageType.FILE_MANIFEST,
            sender_id,
            content=manifest
        )
        return MessageProtocol.encode_message(message)

    @staticmethod
    def create_file_availability(sender_id: str, availability: Dict[str, Any]) -> bytes:
        message = MessageProtocol.create_message(
            MessageType.FILE_AVAILABILITY,
            sender_id,
            content=availability
        )
        return MessageProtocol.encode_message(message)

    @staticmethod
    def create_chunk_request(sender_id: str, recipient_id: str, request: Dict[str, Any]) -> bytes:
        message = MessageProtocol.create_message(
            MessageType.FILE_CHUNK_REQUEST,
            sender_id,
            recipient_id,
            content=request
        )
        return MessageProtocol.encode_message(message)

    @staticmethod
    def create_chunk_response(sender_id: str, recipient_id: str, response: Dict[str, Any]) -> bytes:
        message = MessageProtocol.create_message(
            MessageType.FILE_CHUNK,
            sender_id,
            recipient_id,
            content=response
        )
        return MessageProtocol.encode_message(message)

    @staticmethod
    def create_file_complete(sender_id: str, recipient_id: str, payload: Dict[str, Any]) -> bytes:
        message = MessageProtocol.create_message(
            MessageType.FILE_COMPLETE,
            sender_id,
            recipient_id,
            content=payload
        )
        return MessageProtocol.encode_message(message)