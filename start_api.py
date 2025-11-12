#!/usr/bin/env python3
"""
Startup script for the P2P Messaging API server.
Usage: python start_api.py [--port PORT] [--api-port API_PORT]
"""
import argparse
import os
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Start P2P Messaging API server")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="P2P peer port (default: from PEER_PORT env var or 5000)"
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--identity",
        type=str,
        default=None,
        help="Path to identity file"
    )
    
    args = parser.parse_args()
    
    # Set PEER_PORT environment variable if provided
    if args.port is not None:
        os.environ["PEER_PORT"] = str(args.port)
    
    # Import here so environment variable is set before service initialization
    from src.backend.api import app
    
    print(f"Starting P2P Messaging API server on {args.host}:{args.api_port}")
    print(f"P2P peer will listen on port {os.getenv('PEER_PORT', '5000')}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.api_port,
        log_level="info"
    )

if __name__ == "__main__":
    main()

