import json
import time
from typing import Dict,Tuple, Any, Optional, Set

class MessageValidator:
    def __init__(self):
        self.seen_messages: Set[str] = set()  # Track message IDs to prevent replay
        self.max_message_age = 300  # 5 minutes
        self.max_message_size = 1024 * 1024  # 1MB
        
    def validate_message(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate incoming message"""
        # Check required fields
        required_fields = ["version", "type", "sender_id", "message_id", "timestamp"]
        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"
        
        # Check message ID uniqueness (prevent replay)
        msg_id = message["message_id"]
        if msg_id in self.seen_messages:
            return False, "Duplicate message ID"
        
        # Check timestamp (prevent old messages)
        try:
            msg_time = float(message["timestamp"])
            current_time = time.time()
            
            if abs(current_time - msg_time) > self.max_message_age:
                return False, "Message timestamp too old or in future"
        except:
            return False, "Invalid timestamp"
        
        # Check message type
        valid_types = ["handshake", "text", "ack", "ping", "pong", "error"]
        if message["type"] not in valid_types:
            return False, f"Invalid message type: {message['type']}"
        
        # Type-specific validation
        if message["type"] == "text":
            if "content" not in message or "text" not in message.get("content", {}):
                return False, "Text message missing content"
            
            # Check text length
            text = message["content"]["text"]
            if len(text) > 10000:  # 10K character limit
                return False, "Text message too long"
        
        # Add to seen messages
        self.seen_messages.add(msg_id)
        
        # Clean old message IDs periodically (simple approach)
        if len(self.seen_messages) > 10000:
            self.seen_messages.clear()  # Week 3: Implement proper cleanup
        
        return True, None
    
    def sanitize_text(self, text: str) -> str:
        """Basic text sanitization"""
        # Remove control characters except newline and tab
        sanitized = ''.join(char for char in text 
                          if char == '\n' or char == '\t' or 
                          (ord(char) >= 32 and ord(char) < 127))
        return sanitized[:10000]  # Enforce max length