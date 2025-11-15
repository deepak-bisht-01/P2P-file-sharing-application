# Device Setup Clarification

## Answer: No Code Difference

**Both Device 1 and Device 2 use the exact same codebase.** There are no device-specific code files or configurations.

## What's the Same

✅ **Same codebase** - Both devices run identical code  
✅ **Same Python files** - All backend code is identical  
✅ **Same frontend code** - All React/TypeScript code is identical  
✅ **Same dependencies** - Same `requirements.txt` and `package.json`  

## What's Different (Configuration Only)

The only differences are **runtime configuration** when starting the servers:

### 1. Peer Port (Optional)

If both devices are on the **same machine**, use different peer ports:

**Device 1:**
```bash
python start_api.py --api-port 8000 --port 5000
```

**Device 2:**
```bash
python start_api.py --api-port 8000 --port 5001
```

If devices are on **different machines**, you can use the same port (5000) on both:
```bash
# Both devices can use:
python start_api.py --api-port 8000 --port 5000
```

### 2. IP Addresses (When Connecting)

When connecting peers, use the **actual IP addresses**:

- **Device 1 connects to Device 2**: Use Device 2's IP (e.g., `192.168.1.33`)
- **Device 2 connects to Device 1**: Use Device 1's IP (e.g., `192.168.1.100`)

### 3. API Base URL (Only if Device 2 connects to Device 1's API)

**Normal setup (recommended):** Each device runs its own backend, so no difference needed.

**Alternative setup:** If Device 2's frontend connects to Device 1's API:
- Device 2 frontend needs: `VITE_API_BASE_URL=http://<device1-ip>:8000`
- This is **not recommended** - each device should run its own backend

## Setup Summary

### Device 1
```bash
# Terminal 1: Backend
python start_api.py --api-port 8000 --port 5000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Device 2
```bash
# Terminal 1: Backend (same command, optionally different port)
python start_api.py --api-port 8000 --port 5001

# Terminal 2: Frontend (same command)
cd frontend
npm run dev
```

## Code Files Structure

Both devices have identical file structure:
```
P2P file sharing application/
├── src/                    # Same Python code
│   ├── backend/
│   ├── core/
│   └── security/
├── frontend/               # Same React code
│   └── src/
├── start_api.py           # Same startup script
├── requirements.txt       # Same dependencies
└── README.md              # Same documentation
```

## Identity Files

Each device generates its own identity file (`peer_identity.json`) automatically:
- **Device 1**: Creates `peer_identity.json` with unique peer ID
- **Device 2**: Creates `peer_identity.json` with different unique peer ID

This happens automatically - no manual configuration needed.

## Verification

To verify both devices have the same code:

1. **Check file structure:**
   ```bash
   # Both should show identical structure
   ls -la
   ```

2. **Check code versions:**
   ```bash
   # Both should show same git commit (if using git)
   git log -1
   ```

3. **Check Python packages:**
   ```bash
   # Both should have same packages
   pip list
   ```

## Common Misconception

❌ **Wrong**: "Device 1 needs different code than Device 2"  
✅ **Correct**: "Both devices use the same code, just different runtime configuration"

## Summary

- **Code**: 100% identical
- **Configuration**: Only command-line arguments differ (ports)
- **Runtime**: Each device has its own peer ID and connection state
- **Setup**: Copy the same codebase to both devices

The application is designed to be **peer-to-peer** - each device is equal and runs the same code. The "Device 1" and "Device 2" labels are just for convenience when explaining setup - there's no actual distinction in the code.

