from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
from src.backend.file_transfer import SHARED_DIR

from src.backend.service import p2p_service


class ConnectRequest(BaseModel):
    host: str
    port: int


class MessageRequest(BaseModel):
    recipient_id: Optional[str] = None
    text: str


class DownloadRequest(BaseModel):
    file_id: str


app = FastAPI(title="P2P Messaging API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def get_status():
    return p2p_service.get_status()


@app.get("/api/peers")
def get_peers():
    return {"peers": p2p_service.list_peers()}


@app.get("/api/peers/connected")
def get_connected_peers():
    return {"peers": p2p_service.list_connected_peers()}


@app.post("/api/peers/connect")
def connect_peer(request: ConnectRequest):
    success = p2p_service.connect_to_peer(request.host, request.port)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect to peer")
    return {"status": "connected"}


@app.post("/api/messages")
def create_message(request: MessageRequest):
    if request.recipient_id:
        success = p2p_service.send_text_message(request.recipient_id, request.text)
    else:
        success = p2p_service.broadcast_text_message(request.text)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to queue message")
    return {"status": "queued"}


@app.get("/api/messages")
def list_messages(limit: int = 100):
    limit = max(1, min(limit, 500))
    return {"messages": p2p_service.get_messages(limit=limit)}


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    logger = logging.getLogger(__name__)
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        upload_dir = SHARED_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / file.filename

        with destination.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)

        manifest = p2p_service.share_file(str(destination))
        return {"file": manifest}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/api/files")
def list_files():
    try:
        return p2p_service.list_shared_files()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@app.post("/api/files/download")
def download_file(request: DownloadRequest):
    logger = logging.getLogger(__name__)
    try:
        status = p2p_service.start_file_download(request.file_id)
        return {"transfer": status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as e:
        logger.error(f"Error starting download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")


@app.get("/api/files/transfers")
def list_transfers():
    try:
        return {"transfers": p2p_service.list_transfers()}
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing transfers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list transfers: {str(e)}")


@app.on_event("shutdown")
def shutdown_event():
    p2p_service.shutdown()

