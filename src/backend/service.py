import threading
import socket
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional
from datetime import datetime
import logging
import logging.config
import os
import time
import yaml

from src.core.peer_node import PeerNode
from src.core.connection_manager import ConnectionManager
from src.core.message_protocol import MessageProtocol, MessageType
from src.backend.peer_registry import PeerRegistry
from src.backend.message_queue import MessageQueue
from src.backend.models import Peer, Message
from src.security.peer_identity import PeerIdentity
from src.security.message_validator import MessageValidator
from src.backend.file_transfer import FileTransferManager

logger = logging.getLogger("P2PService")


class P2PService:
    """High-level service that exposes peer operations for the API layer."""

    def __init__(self, port: Optional[int] = None, identity_file: Optional[str] = None):
        # Set up logging first
        self._setup_logging()
        
        # Get port from environment or use default
        if port is None:
            port = int(os.getenv("PEER_PORT", "5000"))
        
        self.port = port
        self.identity = PeerIdentity(identity_file)
        self.validator = MessageValidator()
        self.peer_registry = PeerRegistry()
        self.message_queue = MessageQueue()
        self.messages: Deque[Dict] = deque(maxlen=1000)
        self.lock = threading.RLock()

        # Set up networking components
        self.connection_manager = ConnectionManager(
            message_handler=self._handle_incoming_message,
            peer_registry=self.peer_registry,
            peer_id=self.identity.peer_id
        )
        self.peer_node = PeerNode(
            port=port, 
            peer_id=self.identity.peer_id,
            connection_manager=self.connection_manager,
            peer_registry=self.peer_registry
        )
        self.file_manager = FileTransferManager(self.identity.peer_id, self.connection_manager)

        self._start_components()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # Load logging config if available
            if os.path.exists('config/logging.yaml'):
                with open('config/logging.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                    logging.config.dictConfig(config)
            else:
                # Basic logging setup if config file doesn't exist
                logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
        except Exception as e:
            # Fallback to basic logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logger.warning(f"Could not load logging config: {e}")

    def _start_components(self):
        """Start background components."""
        self.peer_registry.start()
        self.message_queue.start(self._send_message_handler)
        self.peer_node.start()

        # Register self
        self_peer = Peer(
            peer_id=self.identity.peer_id,
            address=self._get_local_ip(),
            port=self.port,
            public_key=self.identity.get_public_key_string()
        )
        self.peer_registry.register_peer(self_peer)

    def shutdown(self):
        """Stop all background components."""
        logger.info("Shutting down P2P service")
        self.message_queue.stop()
        self.peer_registry.stop()
        self.peer_node.stop()

    # ------------------------------------------------------------------
    # Incoming message handling
    # ------------------------------------------------------------------
    def _handle_incoming_message(self, peer_id: str, raw_message: str):
        try:
            message_dict = MessageProtocol.decode_message(raw_message.encode())
            if not message_dict:
                logger.warning("Received message with invalid format")
                return

            is_valid, error = self.validator.validate_message(message_dict)
            if not is_valid:
                logger.warning("Invalid message from %s: %s", peer_id, error)
                return

            self.peer_registry.mark_peer_seen(message_dict["sender_id"])
            msg_type = message_dict["type"]

            if msg_type == MessageType.HANDSHAKE.value:
                self._handle_handshake(message_dict)
            elif msg_type == MessageType.TEXT.value:
                self._handle_text_message(message_dict)
            elif msg_type == MessageType.PING.value:
                self._handle_ping(message_dict)
            elif msg_type == MessageType.FILE_MANIFEST.value:
                self._handle_file_manifest(message_dict)
            elif msg_type == MessageType.FILE_CHUNK_REQUEST.value:
                self._handle_file_chunk_request(message_dict)
            elif msg_type == MessageType.FILE_CHUNK.value:
                self._handle_file_chunk(message_dict)
            elif msg_type == MessageType.FILE_AVAILABILITY.value:
                self._handle_file_availability(message_dict)
            elif msg_type == MessageType.FILE_COMPLETE.value:
                self._handle_file_complete(message_dict)

            self._record_message({
                "direction": "incoming",
                "payload": message_dict,
                "received_at": datetime.utcnow().isoformat()
            })
        except Exception as exc:
            logger.error("Error handling incoming message: %s", exc, exc_info=True)

    def _handle_handshake(self, message: Dict):
        sender_id = message["sender_id"]
        peer_info = message.get("content", {})
        is_response = peer_info.get("handshake_response", False)
        logger.info(f"Received handshake from {sender_id[:8]}: address={peer_info.get('address')}, port={peer_info.get('port')}, is_response={is_response}")
        
        peer = Peer(
            peer_id=sender_id,
            address=peer_info.get("address", "unknown"),
            port=peer_info.get("port", 0),
            public_key=peer_info.get("public_key")
        )
        self.peer_registry.register_peer(peer)
        # Mark peer as seen/online
        self.peer_registry.mark_peer_seen(sender_id)
        
        # ConnectionManager already associates temporary connection ids
        # with real peer ids when the message is received; no need to
        # attempt mapping here using the advertised address/port.
        
        # Wait a moment for connection association to complete
        import time
        time.sleep(0.2)  # Give connection manager time to associate the connection
        
        # Check if connection is active
        active_connections = set(self.connection_manager.get_active_connections())
        logger.info(f"After handshake, active connections: {[c[:8] for c in active_connections]}, looking for {sender_id[:8]}")
        
        # If this is a handshake response, we've completed the bidirectional handshake
        # If it's an initial handshake, send response and file manifests
        if sender_id != self.identity.peer_id:
            if is_response:
                # This is a response to our handshake - connection is now fully established
                logger.info(f"Handshake response received from {sender_id[:8]}, connection established")
                # Send file manifests now that connection is confirmed
                self._send_all_manifests(sender_id)
            else:
                # This is an initial handshake - send response and file manifests
                logger.info(f"Initial handshake from {sender_id[:8]}, sending response and file manifests")
                try:
                    # Send handshake response first
                    self._send_handshake(sender_id, is_response=True)
                    logger.info(f"Sent handshake response to {sender_id[:8]}")
                    # Then send file manifests
                    time.sleep(0.1)  # Small delay between messages
                    self._send_all_manifests(sender_id)
                except Exception as exc:
                    logger.error("Failed to send handshake response to %s: %s", sender_id[:8], exc, exc_info=True)

    def _handle_text_message(self, message: Dict):
        """Handle incoming text message"""
        sender_id = message.get("sender_id", "unknown")
        content = message.get("content", {})
        text = content.get("text", "")
        logger.info("Received text message from %s: %s", sender_id[:8] if len(sender_id) > 8 else sender_id, text[:50])
        
        # Record the message so it appears in the message log
        self._record_message({
            "direction": "incoming",
            "payload": message,
            "received_at": datetime.utcnow().isoformat()
        })

    def _handle_ping(self, message: Dict):
        pong = MessageProtocol.create_message(
            MessageType.PONG,
            self.identity.peer_id,
            message["sender_id"]
        )
        self.connection_manager.send_message(
            message["sender_id"],
            MessageProtocol.encode_message(pong)
        )

    def _send_message_handler(self, message: Message):
        try:
            wire_format = message.to_wire_format()
            encoded = MessageProtocol.encode_message(wire_format)

            if message.recipient_id:
                target_id = message.recipient_id
                active = set(self.connection_manager.get_active_connections())
                
                # Check if target_id is in active connections (could be peer_id or temp address)
                if target_id not in active:
                    # Try to find the peer and connect if needed
                    peer = self.peer_registry.get_peer(target_id)
                    if peer:
                        # Check if we have a connection to this peer by their real peer_id
                        if peer.peer_id in active:
                            target_id = peer.peer_id
                        else:
                            # Try connecting using address:port format
                            temp_id = f"{peer.address}:{peer.port}"
                            if temp_id in active:
                                target_id = temp_id
                            else:
                                # Need to establish connection
                                try:
                                    self.connect_to_peer(peer.address, peer.port)
                                    # Wait a bit for connection to establish
                                    import time
                                    time.sleep(0.2)
                                    active = set(self.connection_manager.get_active_connections())
                                    # Check again after connection
                                    if peer.peer_id in active:
                                        target_id = peer.peer_id
                                    elif temp_id in active:
                                        target_id = temp_id
                                except Exception as exc:
                                    logger.warning("Failed to connect to peer %s: %s", target_id[:8], exc)
                    else:
                        # target_id might be in address:port format, try to connect
                        if ":" in target_id:
                            try:
                                host, port_str = target_id.rsplit(":", 1)
                                port = int(port_str)
                                self.connect_to_peer(host, port)
                                import time
                                time.sleep(0.2)
                                active = set(self.connection_manager.get_active_connections())
                                # Check if connection was established
                                if target_id not in active:
                                    # Check if it's now under a peer_id
                                    for conn_id in active:
                                        peer = self.peer_registry.get_peer(conn_id)
                                        if peer and peer.address == host and peer.port == port:
                                            target_id = conn_id
                                            break
                            except Exception:
                                pass
                
                # Final check - if still not in active, log warning
                if target_id not in active:
                    logger.warning("Target %s not in active connections: %s. Available: %s", 
                                 target_id[:8] if len(target_id) > 8 else target_id, 
                                 list(active)[:5],
                                 [p.peer_id[:8] for p in self.peer_registry.get_all_peers()][:5])
                else:
                    logger.info("Sending message to %s (connection found)", target_id[:8] if len(target_id) > 8 else target_id)
                
                success = self.connection_manager.send_message(target_id, encoded)
                if not success:
                    logger.warning("Failed to send message to %s - connection may be closed", target_id)
                else:
                    logger.info("Message sent successfully to %s", target_id[:8] if len(target_id) > 8 else target_id)
            else:
                active = self.connection_manager.get_active_connections()
                if not active:
                    for peer in self.peer_registry.get_online_peers():
                        if peer.peer_id != self.identity.peer_id:
                            try:
                                self.connect_to_peer(peer.address, peer.port)
                            except Exception:
                                pass
                self.connection_manager.broadcast_message(encoded)

            self._record_message({
                "direction": "outgoing",
                "payload": wire_format,
                "sent_at": datetime.utcnow().isoformat()
            })
        except Exception as exc:
            logger.error("Failed to send message: %s", exc, exc_info=True)

    def _record_message(self, entry: Dict):
        with self.lock:
            self.messages.appendleft(entry)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_status(self) -> Dict:
        try:
            stats = self.message_queue.get_stats()
            file_listing = self.list_shared_files()  # Use service method, not file_manager directly
            transfers = self.file_manager.get_transfers()
            active_transfers = sum(
                1 for transfer in transfers if transfer["status"] in {"pending", "running"}
            )
            return {
                "peer_id": self.identity.peer_id,
                "port": self.port,
                "messages_processed": stats["messages_processed"],
                "messages_failed": stats["messages_failed"],
                "queue_size": stats["queue_size"],
                "active_connections": self.connection_manager.get_active_connections(),
                "files_shared_local": len(file_listing["local"]),
                "files_known_remote": len(file_listing["remote"]),
                "transfers_active": active_transfers,
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            # Return minimal status on error
            return {
                "peer_id": self.identity.peer_id,
                "port": self.port,
                "messages_processed": 0,
                "messages_failed": 0,
                "queue_size": 0,
                "active_connections": [],
                "files_shared_local": 0,
                "files_known_remote": 0,
                "transfers_active": 0,
                "error": str(e)
            }

    def list_peers(self) -> List[Dict]:
        peers = self.peer_registry.get_all_peers()
        return [peer.to_dict() for peer in peers]

    def list_connected_peers(self) -> List[Dict]:
        peers = self.peer_registry.list_connected_peers()
        return [peer.to_dict() for peer in peers]

    def connect_to_peer(self, host: str, port: int) -> bool:
        sock = self.peer_node.connect_to_peer(host, port)
        if not sock:
            return False
        
        # The PeerNode already registers the connection with ConnectionManager.
        # Use the socket local address as the advertised address in the handshake
        try:
            local_addr = sock.getsockname()[0]
        except Exception:
            local_addr = self._get_local_ip()

        temp_peer_id = f"{host}:{port}"
        
        # Small delay to ensure connection is fully registered
        import time
        time.sleep(0.1)

        # send handshake using the temp id assigned for the connection
        # The handshake will be processed and the temp_id will be associated with real peer_id
        try:
            self._send_handshake(temp_peer_id, advertised_address=local_addr)
        except Exception as e:
            logger.warning(f"Failed to send handshake to {temp_peer_id}: {e}")
            # Don't fail the connection if handshake send fails - it might still work

        # Register temp peer (will be updated when real handshake arrives)
        peer = Peer(
            peer_id=temp_peer_id,
            address=host,
            port=port,
            public_key=None
        )
        self.peer_registry.register_peer(peer)
        return True

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def send_text_message(self, recipient_id: str, text: str) -> bool:
        import uuid

        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.identity.peer_id,
            recipient_id=recipient_id,
            message_type=MessageType.TEXT.value,  # Use enum value to ensure consistency
            content={"text": text}
        )
        
        logger.info("Queuing text message to %s: %s", recipient_id[:8] if len(recipient_id) > 8 else recipient_id, text[:50])
        return self.message_queue.put_message(message)

    def broadcast_text_message(self, text: str) -> bool:
        import uuid

        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.identity.peer_id,
            recipient_id=None,
            message_type=MessageType.TEXT.value,  # Use enum value to ensure consistency
            content={"text": text}
        )
        logger.info("Queuing broadcast text message: %s", text[:50])
        return self.message_queue.put_message(message)

    def get_messages(self, limit: int = 100) -> List[Dict]:
        with self.lock:
            return list(list(self.messages)[0:limit])

    # ------------------------------------------------------------------
    # File transfer helpers
    # ------------------------------------------------------------------
    def _send_all_manifests(self, recipient_id: str):
        """Send all local file manifests to a peer"""
        manifests = self.file_manager.list_local_files()
        if not manifests:
            logger.debug(f"No local files to send to {recipient_id[:8]}")
            return
        
        active_connections = set(self.connection_manager.get_active_connections())
        logger.info(f"Sending {len(manifests)} file manifest(s) to {recipient_id[:8]}. Active connections: {[c[:8] for c in active_connections]}")
        
        # Check if recipient_id is in active connections, try alternatives if not
        target_id = recipient_id
        if recipient_id not in active_connections:
            # Try to find by peer registry
            peer = self.peer_registry.get_peer(recipient_id)
            if peer:
                # Try peer_id first
                if peer.peer_id in active_connections:
                    target_id = peer.peer_id
                else:
                    # Try temp address:port format
                    temp_id = f"{peer.address}:{peer.port}"
                    if temp_id in active_connections:
                        target_id = temp_id
                    else:
                        logger.warning(f"Recipient {recipient_id[:8]} not in active connections. Available: {[c[:8] for c in active_connections]}")
                        return
            else:
                logger.warning(f"Recipient {recipient_id[:8]} not found in peer registry and not in active connections")
                return
        
        sent_count = 0
        for manifest in manifests:
            msg = MessageProtocol.create_file_manifest(self.identity.peer_id, manifest)
            if self.connection_manager.send_message(target_id, msg):
                sent_count += 1
            else:
                logger.warning(f"Failed to send file manifest for {manifest.get('file_id', 'unknown')[:8]} to {target_id[:8]}")
        
        logger.info(f"Sent {sent_count}/{len(manifests)} file manifest(s) to {target_id[:8]}")

    def _handle_file_manifest(self, message: Dict):
        sender_id = message["sender_id"]
        manifest = message.get("content", {})
        self.file_manager.register_remote_manifest(sender_id, manifest)

    def _handle_file_chunk_request(self, message: Dict):
        sender_id = message["sender_id"]
        request = message.get("content", {})
        # Ensure sender_id is in connections (might need to update if using temp ID)
        active_connections = self.connection_manager.get_active_connections()
        if sender_id not in active_connections:
            logger.warning(f"Chunk request from {sender_id[:8]} not in active connections: {active_connections}")
        self.file_manager.handle_chunk_request(sender_id, request)

    def _handle_file_chunk(self, message: Dict):
        sender_id = message["sender_id"]
        response = message.get("content", {})
        # Ensure sender_id is in connections
        active_connections = self.connection_manager.get_active_connections()
        if sender_id not in active_connections:
            logger.warning(f"Chunk response from {sender_id[:8]} not in active connections: {active_connections}")
        self.file_manager.handle_chunk_response(sender_id, response)

    def _handle_file_availability(self, message: Dict):
        sender_id = message["sender_id"]
        payload = message.get("content", {})
        self.file_manager.register_remote_availability(sender_id, payload)

    def _handle_file_complete(self, message: Dict):
        sender_id = message["sender_id"]
        payload = message.get("content", {})
        file_id = payload.get("file_id")
        if file_id:
            self.file_manager.handle_download_complete(file_id, sender_id)

    # ------------------------------------------------------------------
    # Public file transfer API
    # ------------------------------------------------------------------
    def share_file(self, upload_path: str) -> Dict:
        shared = self.file_manager.share_local_file(Path(upload_path))
        self.file_manager.broadcast_manifest(shared.file_id)
        return shared.to_manifest(self.identity.peer_id)

    def list_shared_files(self) -> Dict[str, List[Dict]]:
        return {
            "local": self.file_manager.list_local_files(),
            "remote": self.file_manager.list_remote_files(),
        }

    def start_file_download(self, file_id: str) -> Dict:
        remote_entry = self.file_manager.get_remote_file(file_id)
        if not remote_entry:
            raise ValueError("Unknown file requested")

        self._ensure_peers_connected_for_file(file_id, remote_entry.peers)

        status = self.file_manager.start_download(file_id)
        return status.to_dict()

    def list_transfers(self) -> List[Dict]:
        return self.file_manager.get_transfers()


    def _send_handshake(self, recipient_id: str, *, advertised_address: Optional[str] = None, is_response: bool = False):
        payload = {
            "address": advertised_address or self._get_local_ip(),
            "port": self.port,
            "public_key": self.identity.get_public_key_string(),
            "handshake_response": is_response,
        }
        message = MessageProtocol.create_handshake(self.identity.peer_id, payload)
        
        # Try to send using recipient_id, but also try alternatives if it fails
        active_connections = set(self.connection_manager.get_active_connections())
        target_id = recipient_id
        
        logger.debug(f"Attempting to send handshake to {recipient_id[:8]}. Active connections: {[c[:8] for c in active_connections]}")
        
        if recipient_id not in active_connections:
            # Try to find alternative connection ID
            peer = self.peer_registry.get_peer(recipient_id)
            if peer:
                if peer.peer_id in active_connections:
                    target_id = peer.peer_id
                    logger.debug(f"Found connection by peer_id: {target_id[:8]}")
                else:
                    temp_id = f"{peer.address}:{peer.port}"
                    if temp_id in active_connections:
                        target_id = temp_id
                        logger.debug(f"Found connection by temp_id: {target_id[:8]}")
                    else:
                        # Try reverse lookup - find connection by address
                        for conn_id in active_connections:
                            conn_peer = self.peer_registry.get_peer(conn_id)
                            if conn_peer and conn_peer.address == peer.address and conn_peer.port == peer.port:
                                target_id = conn_id
                                logger.debug(f"Found connection by address match: {target_id[:8]}")
                                break
        
        if target_id not in active_connections:
            logger.warning(f"Cannot send handshake - {target_id[:8]} not in active connections: {[c[:8] for c in active_connections]}")
            return False
        
        success = self.connection_manager.send_message(target_id, message)
        if success:
            logger.info(f"Sent handshake to {target_id[:8]} (is_response={is_response})")
        else:
            logger.warning(f"Failed to send handshake to {target_id[:8]}. Connection may be closed.")
        return success

    def _ensure_peers_connected_for_file(self, file_id: str, peer_ids):
        target_peers = {peer for peer in peer_ids if peer and peer != self.identity.peer_id}
        if not target_peers:
            return

        active = set(self.connection_manager.get_active_connections())
        missing = [peer for peer in target_peers if peer not in active]

        for peer_id in missing:
            peer = self.peer_registry.get_peer(peer_id)
            if not peer:
                logger.warning("No registry entry for peer %s when preparing download for %s", peer_id[:8], file_id[:8])
                continue
            try:
                self.connect_to_peer(peer.address, peer.port)
            except Exception as exc:
                logger.warning("Failed to connect to peer %s for file %s: %s", peer_id[:8], file_id[:8], exc)

        if missing:
            deadline = time.time() + 3.0
            while time.time() < deadline:
                active = set(self.connection_manager.get_active_connections())
                if all(peer in active for peer in target_peers):
                    return
                time.sleep(0.1)


# Singleton service instance used by the API layer
p2p_service = P2PService()

