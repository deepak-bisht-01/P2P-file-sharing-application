import socket
import threading
from typing import Dict, Tuple, List
import logging
from collections import defaultdict
from src.backend.models import Peer
 # to avoid circular import
class Connection:
    def __init__(self, socket: socket.socket, address: Tuple[str, int], peer_id: str = None):
        self.socket = socket
        self.address = address
        self.peer_id = peer_id
        self.is_active = True
        self.lock = threading.Lock()

class ConnectionManager:
    def __init__(self, message_handler=None, peer_registry=None):
        self.connections: Dict[str, Connection] = {}  # peer_id -> Connection
        self.address_to_peer: Dict[Tuple[str, int], str] = {}  # address -> peer_id
        self.lock = threading.RLock()
        self.message_handler = message_handler
        self.peer_registry = peer_registry   # ✅ store registry if provided
        self.logger = logging.getLogger('ConnectionManager')
    def add_connection(self, sock: socket.socket, address: Tuple[str, int], peer_id: str = None):
        """Add a new connection"""
        with self.lock:
            if not peer_id:
                peer_id = f"{address[0]}:{address[1]}"
        
            conn = Connection(sock, address, peer_id)
            self.connections[peer_id] = conn
            self.address_to_peer[address] = peer_id

        # ✅ also register the peer
            if self.peer_registry:
                from src.backend.models import Peer  # avoid circular import
                peer = Peer(peer_id=peer_id, address=str(address[0]), port=address[1], status="online")
                self.peer_registry.register_peer(peer)

        # Start handler thread for this connection
            handler_thread = threading.Thread(
                target=self._handle_connection,
                args=(conn,)
        )
            handler_thread.daemon = True
            handler_thread.start()
        
            self.logger.info(f"Added connection for peer {peer_id} (remote address={address})")
    
    def _handle_connection(self, conn: Connection):
        """Handle incoming messages from a connection"""
        buffer = b""
        
        while conn.is_active:
            try:
                data = conn.socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                # Try to extract complete messages (length-prefixed format)
                while len(buffer) >= 4:
                    # Read the length prefix (4 bytes, big-endian)
                    msg_length = int.from_bytes(buffer[:4], byteorder='big')
                    
                    # Check if we have the complete message
                    if len(buffer) < 4 + msg_length:
                        break  # Wait for more data
                    
                    # Extract the message
                    msg_bytes = buffer[4:4+msg_length]
                    buffer = buffer[4+msg_length:]  # Remove from buffer
                    
                    if self.message_handler:
                        try:
                            msg_json = msg_bytes.decode('utf-8')
                            import json
                            msg_dict = json.loads(msg_json)
                            sender_id = msg_dict.get('sender_id', conn.peer_id)
                            
                            # Update connection peer_id if needed (handshake)
                            if sender_id != conn.peer_id and sender_id not in self.connections:
                                self.logger.info(f"Associating temp id {conn.peer_id} with sender_id {sender_id} from message")
                                self.associate_temp_id_with_peer_id(conn.peer_id, sender_id)
                            
                            self.message_handler(sender_id, msg_json)
                        except Exception as e:
                            self.logger.error(f"Error parsing message: {e}")
                            # Fallback
                            self.message_handler(conn.peer_id, msg_bytes.decode('utf-8', errors='replace'))
                        
            except Exception as e:
                self.logger.error(f"Error handling connection {conn.peer_id}: {e}")
                break
        
        # Clean up connection
        self.remove_connection(conn.peer_id)
    
    def send_message(self, peer_id: str, message: bytes) -> bool:
        """Send message to a specific peer (message should be length-prefixed)"""
        with self.lock:
            if peer_id in self.connections:
                conn = self.connections[peer_id]
                try:
                    with conn.lock:
                        conn.socket.sendall(message)
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to send message to {peer_id}: {e}")
                    self.remove_connection(peer_id)
        return False
    
    def broadcast_message(self, message: bytes, exclude_peer: str = None):
        """Broadcast message to all connected peers"""
        with self.lock:
            for peer_id, conn in list(self.connections.items()):
                if peer_id != exclude_peer:
                    self.send_message(peer_id, message)
    
    def remove_connection(self, peer_id: str):
        """Remove a connection"""
        with self.lock:
            if peer_id in self.connections:
                conn = self.connections[peer_id]
                conn.is_active = False
                try:
                    conn.socket.close()
                except:
                    pass
                
                del self.connections[peer_id]
                if conn.address in self.address_to_peer:
                    del self.address_to_peer[conn.address]
                
                self.logger.info(f"Removed connection for peer {peer_id}")
    
    def get_active_connections(self) -> List[str]:
        """Get list of active peer IDs"""
        with self.lock:
            return list(self.connections.keys())
    def associate_temp_id_with_peer_id(self, temp_id: str, real_id: str) -> bool:
        """Replace a temporary peer_id (like 'host:port') with the real peer_id after handshake"""
        with self.lock:
            if temp_id not in self.connections:
                return False

            # Move connection under new key
            conn = self.connections.pop(temp_id)
            conn.peer_id = real_id
            self.connections[real_id] = conn

            # Update address→peer map
            for addr, pid in list(self.address_to_peer.items()):
                if pid == temp_id:
                    self.address_to_peer[addr] = real_id

            self.logger.info(f"Associated temp_id {temp_id} with real_id {real_id}")
            return True

    def dump_state(self) -> Dict:
        """Return a serializable snapshot of the connection manager state for diagnostics."""
        with self.lock:
            return {
                "connections": [
                    {
                        "peer_id": pid,
                        "address": f"{conn.address[0]}:{conn.address[1]}",
                        "is_active": conn.is_active
                    }
                    for pid, conn in self.connections.items()
                ],
                "address_to_peer": {f"{addr[0]}:{addr[1]}": pid for addr, pid in self.address_to_peer.items()}
            }
    
    def on_handshake(self, conn, peer_id_from_handshake):
    # remove the temporary mapping
        old_id = conn.peer_id
        if old_id in self.connections:
            del self.connections[old_id]

    # replace with proper peer_id
        conn.peer_id = peer_id_from_handshake
        self.connections[peer_id_from_handshake] = conn

