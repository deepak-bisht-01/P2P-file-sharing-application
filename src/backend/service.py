import threading
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional
from datetime import datetime
import logging
import logging.config
import os
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
            peer_registry=self.peer_registry
        )
        self.peer_node = PeerNode(port=port, peer_id=self.identity.peer_id)
        self.peer_node.connection_manager = self.connection_manager
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
            address="localhost",
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
        peer = Peer(
            peer_id=sender_id,
            address=peer_info.get("address", "unknown"),
            port=peer_info.get("port", 0),
            public_key=peer_info.get("public_key")
        )
        self.peer_registry.register_peer(peer)
        temp_id = f"{peer.address}:{peer.port}"
        self.connection_manager.associate_temp_id_with_peer_id(temp_id, sender_id)
        self._send_all_manifests(sender_id)

    def _handle_text_message(self, message: Dict):
        # For now, we only record the message. Additional logic could go here.
        pass

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
                success = self.connection_manager.send_message(
                    message.recipient_id,
                    encoded
                )
                if not success:
                    logger.warning("Failed to send message to %s", message.recipient_id)
            else:
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

        temp_peer_id = f"{host}:{port}"
        self.connection_manager.add_connection(sock, (host, port), temp_peer_id)

        handshake = MessageProtocol.create_handshake(
            self.identity.peer_id,
            {
                "address": "localhost",
                "port": self.port,
                "public_key": self.identity.get_public_key_string()
            }
        )
        self.connection_manager.send_message(temp_peer_id, handshake)

        peer = Peer(
            peer_id=temp_peer_id,
            address=host,
            port=port,
            public_key=None
        )
        self.peer_registry.register_peer(peer)
        return True

    def send_text_message(self, recipient_id: str, text: str) -> bool:
        import uuid

        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.identity.peer_id,
            recipient_id=recipient_id,
            message_type="text",
            content={"text": text}
        )

        return self.message_queue.put_message(message)

    def broadcast_text_message(self, text: str) -> bool:
        import uuid

        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.identity.peer_id,
            recipient_id=None,
            message_type="text",
            content={"text": text}
        )
        return self.message_queue.put_message(message)

    def get_messages(self, limit: int = 100) -> List[Dict]:
        with self.lock:
            return list(list(self.messages)[0:limit])

    # ------------------------------------------------------------------
    # File transfer helpers
    # ------------------------------------------------------------------
    def _send_all_manifests(self, recipient_id: str):
        manifests = self.file_manager.list_local_files()
        for manifest in manifests:
            msg = MessageProtocol.create_file_manifest(self.identity.peer_id, manifest)
            self.connection_manager.send_message(recipient_id, msg)

    def _handle_file_manifest(self, message: Dict):
        sender_id = message["sender_id"]
        manifest = message.get("content", {})
        self.file_manager.register_remote_manifest(sender_id, manifest)

    def _handle_file_chunk_request(self, message: Dict):
        sender_id = message["sender_id"]
        request = message.get("content", {})
        self.file_manager.handle_chunk_request(sender_id, request)

    def _handle_file_chunk(self, message: Dict):
        sender_id = message["sender_id"]
        response = message.get("content", {})
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
        status = self.file_manager.start_download(file_id)
        return status.to_dict()

    def list_transfers(self) -> List[Dict]:
        return self.file_manager.get_transfers()


# Singleton service instance used by the API layer
p2p_service = P2PService()

