# Running Two Instances on the Same Device

Yes! You can absolutely run both Device 1 and Device 2 on the same computer. This is perfect for testing and development.

## Quick Setup

### Terminal 1: Device 1 (Port 5000)

```powershell
# Start Device 1 backend
python start_api.py --api-port 8000 --port 5000
```

### Terminal 2: Device 1 Frontend

```powershell
# Start Device 1 frontend
cd frontend
npm run dev
# Will open at http://localhost:5173
```

### Terminal 3: Device 2 (Port 5001)

```powershell
# Start Device 2 backend (use different port!)
python start_api.py --api-port 8001 --port 5001
```

### Terminal 4: Device 2 Frontend

```powershell
# Start Device 2 frontend (in a different directory or use different port)
cd frontend
# Set different API URL for Device 2
$env:VITE_API_BASE_URL="http://localhost:8001"
npm run dev
# Will open at http://localhost:5174 (or next available port)
```

## Important: Different Ports Required

| Service | Device 1 | Device 2 |
|---------|----------|----------|
| **API Server** | 8000 | 8001 |
| **Peer Port** | 5000 | 5001 |
| **Frontend** | 5173 | 5174 (auto) |

## Step-by-Step Instructions

### Step 1: Open 4 Terminal Windows

You'll need 4 separate terminal windows/tabs:
- Terminal 1: Device 1 Backend
- Terminal 2: Device 1 Frontend  
- Terminal 3: Device 2 Backend
- Terminal 4: Device 2 Frontend

### Step 2: Start Device 1

**Terminal 1:**
```powershell
cd "C:\Users\deepa\OneDrive\Desktop\P2P file sharing application"
python start_api.py --api-port 8000 --port 5000
```

Wait for: `Application startup complete`

**Terminal 2:**
```powershell
cd "C:\Users\deepa\OneDrive\Desktop\P2P file sharing application\frontend"
npm run dev
```

Browser opens at: `http://localhost:5173`

### Step 3: Start Device 2

**Terminal 3:**
```powershell
cd "C:\Users\deepa\OneDrive\Desktop\P2P file sharing application"
python start_api.py --api-port 8001 --port 5001
```

Wait for: `Application startup complete`

**Terminal 4:**
```powershell
cd "C:\Users\deepa\OneDrive\Desktop\P2P file sharing application\frontend"
$env:VITE_API_BASE_URL="http://localhost:8001"
npm run dev
```

Browser opens at: `http://localhost:5174` (or next available port)

## Connecting the Two Instances

### In Device 1 Browser (localhost:5173):

1. Open the "Connect to Peer" form
2. Enter:
   - **Host**: `127.0.0.1` (or `localhost`)
   - **Port**: `5001` (Device 2's peer port)
3. Click "Connect"

### In Device 2 Browser (localhost:5174):

1. Open the "Connect to Peer" form
2. Enter:
   - **Host**: `127.0.0.1` (or `localhost`)
   - **Port**: `5000` (Device 1's peer port)
3. Click "Connect"

## Identity Files

Each instance will create its own identity:

- **Device 1**: `peer_identity.json` (port 5000)
- **Device 2**: Will also use `peer_identity.json` but with different peer ID

**Note**: Since both use the same filename, the second instance will overwrite the first if you run them in the same directory. This is usually fine for testing, but if you want to keep separate identities:

### Option A: Use Different Identity Files

**Device 1:**
```powershell
python start_api.py --api-port 8000 --port 5000 --identity peer1_identity.json
```

**Device 2:**
```powershell
python start_api.py --api-port 8001 --port 5001 --identity peer2_identity.json
```

### Option B: Use Different Directories (Recommended for Testing)

Create two copies of the project:

```
P2P-file-sharing-application/
├── device1/
│   ├── src/
│   ├── frontend/
│   └── peer_identity.json (Device 1's identity)
└── device2/
    ├── src/
    ├── frontend/
    └── peer_identity.json (Device 2's identity)
```

## Using PowerShell Scripts (Easier)

### Create `start_device1.ps1`:

```powershell
# Device 1 Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\deepa\OneDrive\Desktop\P2P file sharing application'; python start_api.py --api-port 8000 --port 5000"

# Device 1 Frontend
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\deepa\OneDrive\Desktop\P2P file sharing application\frontend'; npm run dev"
```

### Create `start_device2.ps1`:

```powershell
# Device 2 Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\deepa\OneDrive\Desktop\P2P file sharing application'; python start_api.py --api-port 8001 --port 5001"

# Device 2 Frontend
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\deepa\OneDrive\Desktop\P2P file sharing application\frontend'; `$env:VITE_API_BASE_URL='http://localhost:8001'; npm run dev"
```

Then just run:
```powershell
.\start_device1.ps1
.\start_device2.ps1
```

## Troubleshooting

### Port Already in Use

**Error**: `Address already in use` or `Port 8000 is already in use`

**Solution**: Make sure you're using different ports:
- Device 1: API port 8000, Peer port 5000
- Device 2: API port 8001, Peer port 5001

### Can't Connect Peers

**Problem**: Connection fails between instances

**Solutions**:
1. Verify both backends are running
2. Check you're using correct ports (5000 ↔ 5001)
3. Use `127.0.0.1` or `localhost` for host
4. Check firewall isn't blocking localhost connections

### Same Peer ID

**Problem**: Both instances show the same peer ID

**Solution**: 
- Use `--identity` flag with different filenames
- Or use separate directories for each instance

### Frontend Opens Same Port

**Problem**: Both frontends try to use port 5173

**Solution**: 
- Vite automatically uses the next available port (5174)
- Or manually set: `npm run dev -- --port 5174`

## Quick Test

1. Start both instances (4 terminals)
2. Open both browsers (localhost:5173 and localhost:5174)
3. Connect Device 1 → Device 2 (127.0.0.1:5001)
4. Connect Device 2 → Device 1 (127.0.0.1:5000)
5. Send a test message from Device 1 to Device 2
6. Verify it appears on Device 2

## Summary

✅ **Yes, you can run on the same device!**  
✅ **Use different ports** for each instance  
✅ **4 terminals needed** (2 backends + 2 frontends)  
✅ **Use `127.0.0.1` or `localhost`** for connections  
✅ **Each instance gets its own identity** automatically  

Perfect for testing and development!




