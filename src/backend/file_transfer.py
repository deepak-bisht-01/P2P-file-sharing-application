import base64
import hashlib
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Callable

from src.core.message_protocol import MessageProtocol


DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KiB chunks keep messages under ~90KiB after base64
SHARED_DIR = Path("shared_files")
DOWNLOAD_DIR = Path("downloads")


@dataclass
class SharedFile:
    file_id: str
    file_name: str
    file_size: int
    chunk_size: int
    chunk_count: int
    checksum: str
    path: Path
    created_at: float = field(default_factory=time.time)

    def to_manifest(self, owner_peer_id: str) -> Dict:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "chunk_count": self.chunk_count,
            "checksum": self.checksum,
            "owner": owner_peer_id,
        }


@dataclass
class RemoteFile:
    manifest: Dict
    peers: Set[str] = field(default_factory=set)
    last_update: float = field(default_factory=time.time)


@dataclass
class DownloadStatus:
    file_id: str
    file_name: str
    file_size: int
    chunk_size: int
    chunk_count: int
    destination: Path
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    bytes_received: int = 0
    chunks_completed: int = 0
    peers_used: Set[str] = field(default_factory=set)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "chunk_count": self.chunk_count,
            "destination": str(self.destination),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "bytes_received": self.bytes_received,
            "chunks_completed": self.chunks_completed,
            "peers_used": list(self.peers_used),
            "error": self.error,
        }


class DownloadSession:
    def __init__(
        self,
        status: DownloadStatus,
        remote_peers: Set[str],
        send_request: Callable[[str, bytes], bool],
        sender_id: str,
        manifest_checksum: str,
    ):
        self.status = status
        self.remote_peers = remote_peers.copy()
        self.send_request = send_request
        self.sender_id = sender_id
        self.manifest_checksum = manifest_checksum

        self.chunk_queue: "queue.Queue[int]" = queue.Queue()
        for idx in range(status.chunk_count):
            self.chunk_queue.put(idx)

        self.pending_events: Dict[int, threading.Event] = {}
        self.chunk_payloads: Dict[int, bytes] = {}
        self.pending_lock = threading.RLock()
        self.file_lock = threading.Lock()
        self.session_lock = threading.RLock()
        self.file_handle = None
        self.workers: List[threading.Thread] = []
        self.cancel_event = threading.Event()

    def open_file(self):
        self.status.destination.parent.mkdir(parents=True, exist_ok=True)
        # Pre-allocate file size to support random writes
        with open(self.status.destination, "wb") as output:
            output.truncate(self.status.file_size)
        self.file_handle = open(self.status.destination, "r+b")

    def close_file(self):
        if self.file_handle:
            try:
                self.file_handle.close()
            except OSError:
                pass
            self.file_handle = None

    def stop(self, reason: Optional[str] = None):
        self.cancel_event.set()
        with self.session_lock:
            if reason and not self.status.error:
                self.status.error = reason
            if self.status.status not in {"completed", "failed"}:
                self.status.status = "failed" if reason else "cancelled"
        self.close_file()

    def mark_completed(self):
        with self.session_lock:
            self.status.status = "completed"
            self.status.completed_at = time.time()
        self.close_file()


class FileTransferManager:
    def __init__(self, peer_id: str, connection_manager):
        self.peer_id = peer_id
        self.connection_manager = connection_manager
        self.local_files: Dict[str, SharedFile] = {}
        self.remote_files: Dict[str, RemoteFile] = {}
        self.downloads: Dict[str, DownloadSession] = {}
        self.lock = threading.RLock()

        SHARED_DIR.mkdir(exist_ok=True, parents=True)
        DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

    # ------------------------------------------------------------------
    # Local file sharing
    # ------------------------------------------------------------------
    def share_local_file(self, file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> SharedFile:
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File {file_path} does not exist")

        file_size = file_path.stat().st_size
        checksum = hashlib.sha256()
        chunk_count = (file_size + chunk_size - 1) // chunk_size or 1
        shared_path = SHARED_DIR / file_path.name
        if file_path.resolve() == shared_path.resolve():
            with open(file_path, "rb") as source:
                while True:
                    block = source.read(chunk_size)
                    if not block:
                        break
                    checksum.update(block)
        else:
            with open(file_path, "rb") as source, open(shared_path, "wb") as target:
                while True:
                    block = source.read(chunk_size)
                    if not block:
                        break
                    checksum.update(block)
                    target.write(block)

        file_id = checksum.hexdigest()
        checksum_str = checksum.hexdigest()

        if shared_path.resolve() != file_path.resolve():
            # ensure original file retained; already copied
            pass

        shared_file = SharedFile(
            file_id=file_id,
            file_name=file_path.name,
            file_size=file_size,
            chunk_size=chunk_size,
            chunk_count=chunk_count,
            checksum=checksum_str,
            path=shared_path,
        )

        with self.lock:
            self.local_files[file_id] = shared_file
            self.remote_files.setdefault(
                file_id, RemoteFile(manifest=shared_file.to_manifest(self.peer_id))
            ).peers.add(self.peer_id)

        return shared_file

    def get_local_manifest(self, file_id: str) -> Optional[Dict]:
        with self.lock:
            shared = self.local_files.get(file_id)
            if not shared:
                return None
            return shared.to_manifest(self.peer_id)

    def list_local_files(self) -> List[Dict]:
        with self.lock:
            return [shared.to_manifest(self.peer_id) for shared in self.local_files.values()]

    # ------------------------------------------------------------------
    # Remote file tracking
    # ------------------------------------------------------------------
    def register_remote_manifest(self, peer_id: str, manifest: Dict):
        file_id = manifest["file_id"]
        with self.lock:
            entry = self.remote_files.get(file_id)
            if not entry:
                entry = RemoteFile(manifest=manifest)
                self.remote_files[file_id] = entry
            else:
                # Merge new manifest info, trust newest data
                entry.manifest.update(manifest)
                entry.last_update = time.time()
            entry.peers.add(peer_id)

    def register_remote_availability(self, peer_id: str, availability: Dict):
        file_id = availability["file_id"]
        with self.lock:
            entry = self.remote_files.get(file_id)
            if not entry:
                entry = RemoteFile(manifest={"file_id": file_id})
                self.remote_files[file_id] = entry
            entry.peers.update(set(availability.get("peers", [])))
            entry.peers.add(peer_id)
            entry.last_update = time.time()

    def get_remote_file(self, file_id: str) -> Optional[RemoteFile]:
        with self.lock:
            return self.remote_files.get(file_id)

    def list_remote_files(self) -> List[Dict]:
        with self.lock:
            results = []
            for entry in self.remote_files.values():
                manifest = dict(entry.manifest)
                manifest["peers"] = list(entry.peers)
                results.append(manifest)
            return results

    # ------------------------------------------------------------------
    # Chunk handling helpers
    # ------------------------------------------------------------------
    def get_chunk(self, file_id: str, chunk_index: int) -> Optional[bytes]:
        with self.lock:
            shared = self.local_files.get(file_id)
        if not shared:
            return None

        if chunk_index < 0 or chunk_index >= shared.chunk_count:
            return None

        with open(shared.path, "rb") as handle:
            handle.seek(chunk_index * shared.chunk_size)
            return handle.read(shared.chunk_size)

    def handle_chunk_request(self, sender_id: str, request: Dict):
        file_id = request["file_id"]
        chunk_index = request["chunk_index"]
        chunk_bytes = self.get_chunk(file_id, chunk_index)
        if chunk_bytes is None:
            return
        payload = {
            "file_id": file_id,
            "chunk_index": chunk_index,
            "data": base64.b64encode(chunk_bytes).decode("ascii"),
        }
        message = MessageProtocol.create_chunk_response(self.peer_id, sender_id, payload)
        self.connection_manager.send_message(sender_id, message)

    def handle_chunk_response(self, sender_id: str, response: Dict):
        import logging
        logger = logging.getLogger('FileTransferManager')
        
        file_id = response.get("file_id")
        chunk_index = response.get("chunk_index")
        
        if not file_id or chunk_index is None:
            logger.warning(f"Invalid chunk response from {sender_id[:8]}: missing file_id or chunk_index")
            return
            
        try:
            data = base64.b64decode(response["data"])
        except Exception as e:
            logger.error(f"Failed to decode chunk data from {sender_id[:8]}: {e}")
            return

        session = self.downloads.get(file_id)
        if not session:
            logger.warning(f"Received chunk {chunk_index} for unknown file {file_id[:8]}")
            return

        logger.debug(f"Received chunk {chunk_index} for file {file_id[:8]} from {sender_id[:8]}")
        with session.pending_lock:
            session.chunk_payloads[chunk_index] = data
            if chunk_index in session.pending_events:
                session.pending_events[chunk_index].set()
                logger.debug(f"Notified waiting worker for chunk {chunk_index}")

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------
    def start_download(self, file_id: str, destination: Optional[Path] = None) -> DownloadStatus:
        with self.lock:
            if file_id in self.downloads:
                return self.downloads[file_id].status

            remote = self.remote_files.get(file_id)
            if not remote or "chunk_count" not in remote.manifest:
                raise ValueError("Missing manifest for requested file")

            peers = {peer for peer in remote.peers if peer != self.peer_id}
            if not peers:
                raise ValueError("No peers available for this file")

            manifest = remote.manifest

        destination = destination or DOWNLOAD_DIR / manifest.get("file_name", file_id)

        status = DownloadStatus(
            file_id=file_id,
            file_name=manifest.get("file_name", file_id),
            file_size=manifest.get("file_size", 0),
            chunk_size=manifest.get("chunk_size", DEFAULT_CHUNK_SIZE),
            chunk_count=manifest.get("chunk_count", 0),
            destination=destination,
        )

        session = DownloadSession(
            status=status,
            remote_peers=peers,
            send_request=self._send_request,
            sender_id=self.peer_id,
            manifest_checksum=manifest.get("checksum", ""),
        )
        # Initialize peers_used with the peers we're attempting to use
        session.status.peers_used = peers.copy()
        session.status.status = "running"
        session.open_file()

        with self.lock:
            self.downloads[file_id] = session

        self._spawn_workers(session)

        return status

    def _spawn_workers(self, session: DownloadSession):
        max_workers = max(1, min(len(session.remote_peers), session.status.chunk_count))
        peers_list = list(session.remote_peers)[:max_workers]
        
        if not peers_list:
            session.status.status = "failed"
            session.status.error = "No peers available to download from"
            return
            
        import logging
        logger = logging.getLogger('FileTransferManager')
        logger.info(f"Spawning {len(peers_list)} workers for file {session.status.file_id[:8]} from peers: {[p[:8] for p in peers_list]}")
        
        for peer_id in peers_list:
            worker = threading.Thread(
                target=self._download_worker,
                args=(session, peer_id),
                name=f"download-{session.status.file_id[:8]}-{peer_id[:8]}",
                daemon=True,
            )
            session.workers.append(worker)
            worker.start()

    def _download_worker(self, session: DownloadSession, peer_id: str):
        import logging
        logger = logging.getLogger('FileTransferManager')
        retry_count = 0
        max_retries = 3
        
        while not session.cancel_event.is_set():
            try:
                chunk_index = session.chunk_queue.get_nowait()
            except queue.Empty:
                # no more chunks
                break

            event = threading.Event()
            with session.pending_lock:
                session.pending_events[chunk_index] = event

            request_payload = {"file_id": session.status.file_id, "chunk_index": chunk_index}
            request_message = MessageProtocol.create_chunk_request(
                self.peer_id, peer_id, request_payload
            )
            success = self.connection_manager.send_message(peer_id, request_message)
            if not success:
                logger.warning(f"Failed to send chunk request {chunk_index} to peer {peer_id[:8]}")
                with session.pending_lock:
                    session.pending_events.pop(chunk_index, None)
                session.chunk_queue.put(chunk_index)
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Too many failures with peer {peer_id[:8]}, stopping worker")
                    break
                time.sleep(0.5)
                continue

            retry_count = 0  # Reset on success
            received = event.wait(timeout=10)  # Increased timeout
            if not received:
                logger.warning(f"Timeout waiting for chunk {chunk_index} from peer {peer_id[:8]}")
                with session.pending_lock:
                    session.pending_events.pop(chunk_index, None)
                session.chunk_queue.put(chunk_index)
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Too many timeouts with peer {peer_id[:8]}, stopping worker")
                    break
                continue

            with session.pending_lock:
                data = session.chunk_payloads.pop(chunk_index, None)
                session.pending_events.pop(chunk_index, None)

            if data is None:
                session.chunk_queue.put(chunk_index)
                continue

            with session.file_lock:
                try:
                    session.file_handle.seek(chunk_index * session.status.chunk_size)
                    session.file_handle.write(data)
                except OSError as exc:
                    session.stop(f"I/O error writing chunk: {exc}")
                    return

            with session.session_lock:
                session.status.bytes_received += len(data)
                session.status.chunks_completed += 1
                session.status.peers_used.add(peer_id)

            if session.status.chunks_completed >= session.status.chunk_count:
                self._finalise_download(session)
                break

        # Wait for remaining workers to finish if this worker completed the queue
        if (
            session.status.chunks_completed >= session.status.chunk_count
            and not session.cancel_event.is_set()
        ):
            self._finalise_download(session)

    def _finalise_download(self, session: DownloadSession):
        if session.status.status == "completed":
            return
        session.mark_completed()
        # verify checksum if available
        if session.manifest_checksum:
            with open(session.status.destination, "rb") as handle:
                computed = hashlib.sha256(handle.read()).hexdigest()
            if computed != session.manifest_checksum:
                session.status.status = "failed"
                session.status.error = "Checksum mismatch after download"
                session.status.completed_at = time.time()
        if session.status.status == "completed":
            self.broadcast_availability(session.status.file_id)

    def _send_request(self, peer_id: str, message: bytes) -> bool:
        return self.connection_manager.send_message(peer_id, message)

    def handle_download_complete(self, file_id: str, peer_id: str):
        status = self.downloads.get(file_id)
        if status:
            status.status.peers_used.add(peer_id)

    def get_transfers(self) -> List[Dict]:
        with self.lock:
            return [session.status.to_dict() for session in self.downloads.values()]

    def broadcast_manifest(self, file_id: str):
        manifest = self.get_local_manifest(file_id)
        if not manifest:
            return
        message = MessageProtocol.create_file_manifest(self.peer_id, manifest)
        self.connection_manager.broadcast_message(message)

    def broadcast_availability(self, file_id: str):
        with self.lock:
            entry = self.remote_files.get(file_id)
            if not entry:
                manifest = self.local_files.get(file_id)
                if manifest:
                    peers = {self.peer_id}
                else:
                    return
            else:
                peers = entry.peers | {self.peer_id}
        payload = {"file_id": file_id, "peers": list(peers)}
        message = MessageProtocol.create_file_availability(self.peer_id, payload)
        self.connection_manager.broadcast_message(message)


