from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from src.backend.service import p2p_service


class ConnectRequest(BaseModel):
    host: str
    port: int


class MessageRequest(BaseModel):
    recipient_id: Optional[str] = None
    text: str


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


@app.on_event("shutdown")
def shutdown_event():
    p2p_service.shutdown()

