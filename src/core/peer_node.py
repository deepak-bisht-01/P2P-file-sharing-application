import socket
import threading
import json
import logging
from typing import Dict, Tuple, Optional

# import these from your backend
from src.core.connection_manager import ConnectionManager
from src.backend.peer_registry import PeerRegistry

class PeerNode:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, peer_id: str = None, 
                 connection_manager: ConnectionManager = None, peer_registry: PeerRegistry = None):
        self.host = host
        self.port = port
        self.peer_id = peer_id
        self.server_socket = None
        self.is_running = False
        self.logger = logging.getLogger(f'PeerNode-{port}')

        # Use provided connection_manager and registry, or create defaults
        if connection_manager:
            self.connection_manager = connection_manager
        else:
            self.peer_registry = peer_registry or PeerRegistry()
            if not peer_registry:
                self.peer_registry.start()
            
            self.connection_manager = ConnectionManager(
                message_handler=self._handle_message,
                peer_registry=self.peer_registry,
                peer_id=self.peer_id
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
        """Connect to another peer"""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)
            try:
                peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception:
                pass
            peer_socket.connect((target_host, target_port))
            # Don't set timeout to None here - let connection_manager set it properly
            # This ensures consistent timeout handling
            self.logger.info(f"Connected to peer at {target_host}:{target_port}")
            
            # ✅ Add connection into manager
            if self.connection_manager:
                self.connection_manager.add_connection(peer_socket, (target_host, target_port))
            
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
        self.logger.info(f"Message from {peer_id}: {message}")
