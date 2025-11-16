# P2P File Sharing Application

A peer-to-peer messaging and file sharing application with a modern React frontend and Python backend.

## Features

- **P2P Networking**: Direct peer-to-peer connections for messaging and file sharing
- **File Transfer**: Chunked file transfer with multi-peer download support for faster speeds
- **Real-time Dashboard**: React-based UI for monitoring peers, messages, and file transfers
- **Interactive UI**: Real-time download progress display with transfer speed and status
- **REST API**: FastAPI backend exposing peer operations and file transfer endpoints
- **Message Queue**: Thread-safe message processing with priority support
- **Peer Registry**: Automatic peer discovery and status tracking
- **Serverless Architecture**: Fully decentralized - no central server required

## Project Structure

```
P2P-file-sharing-application/
├── src/                    # Python backend source
│   ├── backend/           # API and service layer
│   │   └── file_transfer.py  # File transfer manager
│   ├── core/              # Core P2P networking
│   ├── security/          # Identity and validation
│   └── cli/               # Command-line interface
├── frontend/              # React frontend
│   └── src/
│       ├── components/    # React components
│       │   └── FileTransferPanel.tsx  # File transfer UI
│       ├── api.ts         # API client
│       └── types.ts       # TypeScript types
├── shared_files/          # Directory for shared/downloaded files
├── config/                # Configuration files
├── logs/                  # Application logs
└── requirements.txt       # Python dependencies
```

## Prerequisites

- Python 3.9+
- Node.js 18+ and npm
- (Optional) Docker and Docker Compose

## Installation

### Backend

1. Install Python dependencies:
```bash
cd P2P-file-sharing-application
pip install -r requirements.txt
```

### Frontend

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Run API Server with Startup Script (Recommended)

**On Windows (PowerShell):**
```powershell
# From project root
python start_api.py --port 5000 --api-port 8000
# OR use explicit path notation:
.\start_api.py --port 5000 --api-port 8000
```

**On Linux/Mac:**
```bash
# From project root
python start_api.py --port 5000 --api-port 8000
```

This starts:
- P2P peer on port 5000
- FastAPI server on port 8000

### Option 2: Run API Server with Uvicorn Directly

**On Windows (PowerShell):**
```powershell
# Set peer port (optional, defaults to 5000)
$env:PEER_PORT=5000

# Start the API server
python -m uvicorn src.backend.api:app --host 0.0.0.0 --port 8000
```

**On Linux/Mac:**
```bash
# Set peer port (optional, defaults to 5000)
export PEER_PORT=5000

# Start the API server
python -m uvicorn src.backend.api:app --host 0.0.0.0 --port 8000
```

### Frontend Development Server

In a separate terminal:

**On Windows (PowerShell):**
```powershell
cd frontend

# Set API URL if different from default
$env:VITE_API_BASE_URL="http://localhost:8000"

# Start development server
npm run dev
```

**On Linux/Mac:**
```bash
cd frontend

# Set API URL if different from default
export VITE_API_BASE_URL=http://localhost:8000

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port Vite assigns).

## Usage

1. **Start the API server** (see above)
2. **Start the frontend** (see above)
3. **Open the dashboard** in your browser
4. **Connect to peers** by entering their host and port
5. **Send messages** by selecting a peer and typing a message
6. **Share files** by uploading files through the File Transfer panel
7. **Download files** by selecting available files from connected peers
8. **Monitor transfers** in real-time with progress bars and speed indicators

### File Transfer Features

- **Multi-Peer Download**: When multiple peers have the same file, chunks are downloaded from different peers simultaneously, significantly increasing download speed
- **Chunked Transfer**: Large files are split into chunks (default 64KB) for efficient transfer and resumability
- **Real-time Progress**: Live updates showing download progress, transfer speed, and status for each file
- **Interactive UI**: Upload files, browse available files from peers, and manage active transfers

## Docker Deployment

Build and run with Docker Compose:

```bash
docker-compose up --build
```

This starts multiple peer instances on ports 5001, 5002, and 5003.

## Configuration

### Environment Variables

- `PEER_PORT`: Port for the P2P peer node (default: 5000)
- `VITE_API_BASE_URL`: Frontend API base URL (default: http://localhost:8000)

### Logging

Logging configuration is in `config/logging.yaml`. Logs are written to the `logs/` directory.

## API Endpoints

### Peer Management
- `GET /api/status` - Get peer status and statistics
- `GET /api/peers` - List all known peers
- `GET /api/peers/connected` - List connected peers
- `POST /api/peers/connect` - Connect to a peer

### Messaging
- `POST /api/messages` - Send a message
- `GET /api/messages` - Get message history

### File Transfer
- `POST /api/files/upload` - Upload a file to share with peers
- `GET /api/files/list` - List available files from connected peers
- `POST /api/files/download` - Request to download a file from a peer
- `GET /api/files/transfers` - Get status of active file transfers
- `GET /api/files/transfers/{transfer_id}` - Get detailed status of a specific transfer

## Operating System Concepts Used

This project implements several fundamental operating system concepts:

### 1. **Threading and Concurrency**
- **Location**: `src/backend/file_transfer.py`, `src/core/connection_manager.py`, `src/backend/message_queue.py`
- **Implementation**: 
  - Multiple threads handle concurrent file chunk downloads from different peers
  - Each peer connection runs in its own thread for non-blocking I/O
  - Message queue processor runs in a separate daemon thread
  - File transfer manager uses thread pools for parallel chunk requests
- **OS Concept**: Multi-threading enables concurrent operations, improving performance and responsiveness

### 2. **File I/O Operations**
- **Location**: `src/backend/file_transfer.py`
- **Implementation**:
  - File reading/writing using Python's `open()` with binary mode
  - Chunked file access using `seek()` and `read()` for random access
  - Atomic file operations to prevent corruption during concurrent writes
  - File metadata management (size, checksums, chunk mapping)
- **OS Concept**: Direct file system operations for persistent storage and efficient data access

### 3. **Socket Programming and Network I/O**
- **Location**: `src/core/peer_node.py`, `src/core/connection_manager.py`
- **Implementation**:
  - TCP socket creation, binding, and listening (`socket.socket()`, `bind()`, `listen()`)
  - Non-blocking connection handling with `accept()` in separate threads
  - Socket send/receive operations with error handling
  - Connection state management and cleanup
- **OS Concept**: Network socket abstraction for inter-process communication across network boundaries

### 4. **Process Synchronization (Locks)**
- **Location**: `src/backend/file_transfer.py`, `src/core/connection_manager.py`, `src/backend/message_queue.py`
- **Implementation**:
  - `threading.RLock()` (reentrant locks) for thread-safe access to shared data structures
  - Lock-protected critical sections for connection dictionaries and transfer state
  - Queue synchronization using `queue.PriorityQueue` for thread-safe message passing
- **OS Concept**: Mutual exclusion prevents race conditions in multi-threaded environments

### 5. **Memory Management**
- **Location**: Throughout the codebase
- **Implementation**:
  - Buffer management for chunked file transfers (64KB chunks)
  - Memory-efficient streaming for large files
  - Proper resource cleanup (socket.close(), file.close())
  - Garbage collection of completed transfers
- **OS Concept**: Efficient memory usage and resource deallocation

### 6. **Inter-Process Communication (IPC)**
- **Location**: `src/core/message_protocol.py`, `src/backend/service.py`
- **Implementation**:
  - Message-based communication protocol between peers
  - JSON serialization/deserialization for structured data exchange
  - Request-response pattern for file metadata and chunk requests
- **OS Concept**: Structured communication protocol for distributed system coordination

### 7. **Error Handling and Resource Management**
- **Location**: Throughout the codebase
- **Implementation**:
  - Try-except blocks for graceful error handling
  - Automatic resource cleanup using context managers and finally blocks
  - Connection retry logic and timeout handling
- **OS Concept**: Robust error recovery and resource lifecycle management

## Development

### Running Tests

```bash
pytest tests/
```

### CLI Mode

You can also run the application in CLI mode:

```bash
p2p-chat --port 5000
```

## Troubleshooting

### Port Already in Use

If you see the error `[Errno 10048] only one usage of each socket address (protocol/network address/port) is normally permitted`, it means the server is already running on that port.

**Check if server is running:**
```powershell
# Windows PowerShell
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

**Stop the existing server:**
```powershell
# Windows PowerShell - Find and kill the process
$processId = (Get-NetTCPConnection -LocalPort 8000).OwningProcess
Stop-Process -Id $processId -Force

# Or manually: Find PID from netstat, then:
# Stop-Process -Id <PID> -Force
```

```bash
# Linux/Mac - Find and kill the process
kill $(lsof -t -i:8000)
```

**Alternative: Use a different port:**
```powershell
# Windows PowerShell
python start_api.py --port 5000 --api-port 8001
```

### Peer Connection Issues Between Devices

If you cannot establish connections between two separate devices:

**1. Test the connection first:**
```powershell
# Windows PowerShell - Test if peer is reachable
python test_peer_connection.py <device-ip> <port>

# Example:
python test_peer_connection.py 192.168.1.100 5000
```

**2. Verify both devices are set up correctly:**
- **Device 1**: `python start_api.py --port 5000 --api-port 8000`
- **Device 2**: `python start_api.py --port 5001 --api-port 8000` (or same port if different machines)

**3. Check IP addresses:**
```powershell
# Windows PowerShell - Get your IP address
ipconfig
# Look for "IPv4 Address" under your network adapter (e.g., 192.168.1.100)
```

**4. Use actual IP addresses, not localhost:**
- ❌ **Wrong**: `127.0.0.1:5000` or `localhost:5000` (only works on same machine)
- ✅ **Correct**: `192.168.1.100:5000` (use the actual IP address)

**5. Check Windows Firewall:**
```powershell
# Allow Python through Windows Firewall
# Go to: Windows Security > Firewall & network protection > Allow an app through firewall
# Add Python and allow both Private and Public networks
```

**6. Test network connectivity:**
```powershell
# Ping the other device
ping <device-ip>

# Test if port is reachable
Test-NetConnection -ComputerName <device-ip> -Port <peer-port>
```

**7. Common connection errors and solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Firewall blocking or peer not running | Check firewall, verify peer is running |
| Connection refused | Wrong port or peer not listening | Verify port number, check peer logs |
| Network unreachable | Wrong IP address or different network | Use correct IP, ensure same network |
| 400 Bad Request | Connection failed | Use diagnostic script to test connection |

**8. Verify connection in logs:**
- Check backend console for: `"Successfully connected to peer at <ip>:<port>"`
- Check for errors: `"Failed to connect to peer"` or `"Connection timeout"`

### Other Common Issues

- **Frontend can't connect**: Ensure the API server is running and `VITE_API_BASE_URL` is set correctly
- **Module not found errors**: Make sure you're running commands from the project root directory
- **Handshake fails**: Wait a few seconds after connecting - handshake may take time


