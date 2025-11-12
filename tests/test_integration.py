import pytest
import threading
import time
import socket
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Ensure the src package is importable when running tests without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Import all components
from core.peer_node import PeerNode
from core.connection_manager import ConnectionManager
from core.message_protocol import MessageProtocol, MessageType
from security.peer_identity import PeerIdentity
from security.message_validator import MessageValidator
from backend.message_queue import MessageQueue
from backend.peer_registry import PeerRegistry
from backend.models import Peer, Message

class TestIntegration:
    """Integration tests for Week 1 functionality"""
    
    def test_peer_connection(self):
        """Test basic peer-to-peer connection"""
        # Create two peer nodes
        peer1 = PeerNode(port=6001)
        peer2 = PeerNode(port=6002)
        
        # Start peer1
        peer1.start()
        time.sleep(0.5)  # Allow server to start
        
        # Connect peer2 to peer1
        sock = peer2.connect_to_peer('localhost', 6001)
        
        assert sock is not None
        assert sock.getpeername() == ('127.0.0.1', 6001)
        
        # Cleanup
        sock.close()
        peer1.stop()
    
    def test_message_exchange(self):
        """Test message exchange between peers"""
        received_messages = []
        
        def message_handler(peer_id, message):
            received_messages.append((peer_id, message))
        
        # Setup connection managers
        cm1 = ConnectionManager(message_handler)
        cm2 = ConnectionManager(message_handler)
        
        # Create socket pair
        sock1, sock2 = socket.socketpair()
        
        # Add connections
        cm1.add_connection(sock1, ('test', 1), 'peer2')
        cm2.add_connection(sock2, ('test', 2), 'peer1')
        
        # Send message from cm1 to cm2
        test_message = MessageProtocol.create_text_message('peer1', 'peer2', 'Hello!')
        cm1.send_message('peer2', test_message)
        
        # Wait for message
        time.sleep(0.5)
        
        # Check received
        assert len(received_messages) > 0
        peer_id, raw_msg = received_messages[0]
        message = MessageProtocol.decode_message(raw_msg.encode())
        
        assert message['type'] == 'text'
        assert message['content']['text'] == 'Hello!'
    
    def test_message_validation(self):
        """Test message validation"""
        validator = MessageValidator()
        
        # Valid message
        valid_msg = {
            "version": "1.0",
            "type": "text",
            "sender_id": "test-peer",
            "message_id": "msg-123",
            "timestamp": time.time(),
            "content": {"text": "Hello"}
        }
        
        is_valid, error = validator.validate_message(valid_msg)
        assert is_valid is True
        assert error is None
        
        # Invalid message (missing field)
        invalid_msg = {
            "version": "1.0",
            "type": "text",
            "sender_id": "test-peer"
        }
        
        is_valid, error = validator.validate_message(invalid_msg)
        assert is_valid is False
        assert "Missing required field" in error
    
    def test_peer_registry(self):
        """Test peer registry functionality"""
        registry = PeerRegistry()
        registry.start()
        
        # Register peer
        peer = Peer(
            peer_id="test-peer-1",
            address="192.168.1.100",
            port=5000
        )
        
        is_new = registry.register_peer(peer)
        assert is_new is True
        
        # Get peer
        retrieved = registry.get_peer("test-peer-1")
        assert retrieved is not None
        assert retrieved.peer_id == "test-peer-1"
        
        # Update peer
        registry.mark_peer_seen("test-peer-1")
        assert retrieved.status == "online"
        
        # Get online peers
        online = registry.get_online_peers()
        assert len(online) == 1
        
        registry.stop()
    
    def test_message_queue(self):
        """Test message queue functionality"""
        processed = []
        
        def handler(message):
            processed.append(message)
        
        queue = MessageQueue()
        queue.start(handler)
        
        # Add messages
        msg1 = Message(
            message_id="msg-1",
            sender_id="peer1",
            recipient_id="peer2",
            message_type="text",
            content={"text": "First"}
        )
        
        msg2 = Message(
            message_id="msg-2",
            sender_id="peer1",
            recipient_id="peer2",
            message_type="text",
            content={"text": "Second"}
        )
        
        queue.put_message(msg1, priority=5)
        queue.put_message(msg2, priority=1)  # Higher priority
        
        # Wait for processing
        time.sleep(1)
        
        # Check order (msg2 should be processed first due to priority)
        assert len(processed) == 2
        assert processed[0].message_id == "msg-2"
        assert processed[1].message_id == "msg-1"
        
        queue.stop()
    
    def test_peer_identity(self):
        """Test peer identity generation and verification"""
        # Create identity
        identity = PeerIdentity("test_identity.json")
        peer_id = identity.peer_id
        
        assert peer_id is not None
        assert '-' in peer_id
        
        # Get public key
        pub_key = identity.get_public_key_string()
        assert pub_key.startswith('-----BEGIN PUBLIC KEY-----')
        
        # Verify peer ID matches public key
        is_valid = identity.verify_peer_id(peer_id, pub_key)
        assert is_valid is True
        
        # Cleanup
        import os
        if os.path.exists("test_identity.json"):
            os.remove("test_identity.json")

def test_full_integration():
    """Test full system integration"""
    print("\n=== Running Full Integration Test ===\n")
    
    # Create two complete peer systems
    from cli.interface import P2PCLI
    
    # Peer 1
    cli1 = P2PCLI(7001, "peer1_identity.json")
    thread1 = threading.Thread(target=cli1.start)
    thread1.daemon = True
    thread1.start()
    
    # Peer 2
    cli2 = P2PCLI(7002, "peer2_identity.json")
    thread2 = threading.Thread(target=cli2.start)
    thread2.daemon = True
    thread2.start()
    
    # Allow systems to start
    time.sleep(2)
    
    print("✓ Both peers started successfully")
    
    # Simulate peer 2 connecting to peer 1
    sock = cli2.peer_node.connect_to_peer('localhost', 7001)
    assert sock is not None
    
    print("✓ Peer 2 connected to Peer 1")
    
    # Add connection to peer 2's connection manager
    cli2.connection_manager.add_connection(sock, ('localhost', 7001), 'temp-peer1')
    
    # Send handshake
    handshake = MessageProtocol.create_handshake(
        cli2.identity.peer_id,
        {
            "address": "localhost",
            "port": 7002,
            "public_key": cli2.identity.get_public_key_string()
        }
    )
    cli2.connection_manager.send_message('temp-peer1', handshake)
    
    time.sleep(1)
    
    print("✓ Handshake completed")
    
    # Check if peer 1 registered peer 2
    peer2_in_registry = cli1.peer_registry.get_peer(cli2.identity.peer_id)
    assert peer2_in_registry is not None
    
    print("✓ Peer registry updated")
    
    # Send a text message
    import uuid
    test_message = Message(
        message_id=str(uuid.uuid4()),
        sender_id=cli2.identity.peer_id,
        recipient_id=cli1.identity.peer_id,
        message_type="text",
        content={"text": "Integration test message!"}
    )
    
    cli2.message_queue.put_message(test_message)
    
    time.sleep(1)
    
    print("✓ Message sent successfully")
    print("\n=== Integration Test Completed ===\n")
    
    # Cleanup
    import os
    for f in ["peer1_identity.json", "peer2_identity.json"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    # Run integration test
    test_full_integration()