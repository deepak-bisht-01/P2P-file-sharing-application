import socket
import threading
import json
import logging
from typing import Dict, Tuple, Optional

# import these from your backend
from src.core.connection_manager import ConnectionManager
from src.backend.peer_registry import PeerRegistry

class PeerNode:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, peer_id: str = None):
        self.host = host
        self.port = port
        self.peer_id = peer_id
        self.server_socket = None
        self.is_running = False
        self.logger = logging.getLogger(f'PeerNode-{port}')

        # ✅ create registry
        self.peer_registry = PeerRegistry()
        self.peer_registry.start()

        # ✅ create connection manager with registry
        self.connection_manager = ConnectionManager(
            message_handler=self._handle_message,
            peer_registry=self.peer_registry
        )
    
    def start(self):
        """Start the peer node server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.is_running = True
            
            self.logger.info(f"Peer node started on {self.host}:{self.port}")
            
            # Accept connections in a separate thread
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start peer node: {e}")
            raise
    
    def _accept_connections(self):
        """Accept incoming connections"""
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"New connection from {address}")
                
                # ✅ Hand off to connection manager
                if self.connection_manager:
                    self.connection_manager.add_connection(client_socket, address)
                    
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def connect_to_peer(self, target_host: str, target_port: int) -> Optional[socket.socket]:
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((target_host, target_port))
            self.logger.info(f"Connected to peer at {target_host}:{target_port}")
        
        # Add to manager under temp ID
            if self.connection_manager:
                self.connection_manager.add_connection(peer_socket, (target_host, target_port))

            # 🔑 Immediately send handshake with our peer_id
                handshake = {"type": "handshake", "peer_id": self.peer_id}
                self.connection_manager.send_message(f"{target_host}:{target_port}", json.dumps(handshake).encode())

            return peer_socket
        except Exception as e:
            self.logger.error(f"Failed to connect to peer: {e}")
            return None

    
    def stop(self):
        """Stop the peer node"""
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()

    # placeholder handler
    def _handle_message(self, peer_id: str, message: str):
        try:
            msg = json.loads(message)
            if msg.get("type") == "handshake":
                real_id = msg["peer_id"]
                self.connection_manager.associate_temp_id_with_peer_id(peer_id, real_id)
                self.logger.info(f"✓ Handshake from {real_id}")
                return
        except Exception:
            pass  # not JSON or not a handshake

    # Otherwise treat it as normal app message
        self.logger.info(f"Message from {peer_id}: {message}")
