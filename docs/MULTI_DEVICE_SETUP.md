# Multi-Device Setup Guide

This guide explains how to set up the P2P file sharing application on multiple devices.

## Quick Start

### Device 1 Setup

1. **Start the backend server:**
   ```bash
   python start_api.py --api-port 8000 --port 5000
   ```

2. **Find Device 1's IP address:**
   ```bash
   # Windows:
   ipconfig
   # Look for "IPv4 Address" (e.g., 192.168.1.100)
   
   # Linux/Mac:
   ifconfig
   # or
   hostname -I
   ```

3. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

### Device 2 Setup

**Recommended: Run your own backend on Device 2**

1. **Start the backend server (use a different peer port):**
   ```bash
   python start_api.py --api-port 8000 --port 5001
   ```
   Note: Using port 5001 to avoid conflicts if both devices are on the same machine

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

## Connecting Peers Between Devices

### Step 1: Get IP Addresses

- **Device 1 IP**: Found using `ipconfig` or `ifconfig` (e.g., `192.168.1.100`)
- **Device 2 IP**: Found using `ipconfig` or `ifconfig` (e.g., `192.168.1.101`)

### Step 2: Connect from Device 1 to Device 2

1. Open the web app on Device 1
2. In the "Connect to Peer" form:
   - **Host**: Enter Device 2's IP address (e.g., `192.168.1.101`)
   - **Port**: Enter Device 2's peer port (e.g., `5001`)
3. Click "Connect"

### Step 3: Connect from Device 2 to Device 1

1. Open the web app on Device 2
2. In the "Connect to Peer" form:
   - **Host**: Enter Device 1's IP address (e.g., `192.168.1.100`)
   - **Port**: Enter Device 1's peer port (e.g., `5000`)
3. Click "Connect"

## Important Notes

### ✅ DO:
- Use actual IP addresses (192.168.x.x) when connecting between devices
- Use different peer ports if running on the same machine (5000, 5001, 5002, etc.)
- Ensure both devices are on the same network
- Check firewall settings allow connections on peer ports

### ❌ DON'T:
- Use `localhost` or `127.0.0.1` when connecting to another device
- Use the same peer port on both devices if they're on the same machine
- Forget to start the backend server on each device

## Troubleshooting

### Error: ERR_CONNECTION_REFUSED on Device 2

**Problem**: Device 2 cannot connect to its backend server.

**Solution**:
1. Make sure you started the backend server on Device 2:
   ```bash
   python start_api.py --api-port 8000 --port 5001
   ```
2. Check that the server is running (you should see "Application startup complete" in the terminal)

### Error: 400 Bad Request when connecting peers

**Problem**: Cannot establish peer-to-peer connection.

**Solutions**:
1. **Verify both backend servers are running**
   - Device 1: `python start_api.py --api-port 8000 --port 5000`
   - Device 2: `python start_api.py --api-port 8000 --port 5001`

2. **Check IP addresses are correct**
   - Use `ipconfig` (Windows) or `ifconfig` (Linux/Mac) to verify
   - Don't use `localhost` or `127.0.0.1` for cross-device connections

3. **Check firewall settings**
   - Windows: Allow Python through Windows Firewall
   - Linux: Check `iptables` or `ufw` rules
   - Ensure ports 5000, 5001, and 8000 are not blocked

4. **Verify network connectivity**
   ```bash
   # From Device 1, test connection to Device 2:
   # Windows PowerShell:
   Test-NetConnection -ComputerName <device2-ip> -Port 5001
   
   # Linux/Mac:
   telnet <device2-ip> 5001
   ```

### Error: Can't see peers from other device

**Problem**: Peers are connected but not visible in the peer list.

**Solutions**:
1. Wait a few seconds - peer discovery takes a moment
2. Click "Refresh" button in the Peer List
3. Check that both devices show "Active Connections: 1" in the status panel
4. Verify the handshake completed successfully (check backend logs)

## Network Configuration

### Same Network (Recommended)

Both devices should be on the same local network (same WiFi or Ethernet network).

- Device 1: `192.168.1.100`
- Device 2: `192.168.1.101`

### Different Networks

If devices are on different networks, you'll need:
- Port forwarding configured on routers
- Or use a VPN to create a virtual network
- Or use a tunneling service (ngrok, etc.)

## Port Summary

| Service | Default Port | Description |
|---------|-------------|-------------|
| API Server | 8000 | HTTP API for frontend |
| Peer Node | 5000 | P2P peer-to-peer connections |

When running multiple instances on the same machine, use different peer ports:
- Instance 1: Peer port 5000
- Instance 2: Peer port 5001
- Instance 3: Peer port 5002

## Example Setup

### Scenario: Two devices on the same network

**Device 1 (192.168.1.100):**
```bash
# Terminal 1: Backend
python start_api.py --api-port 8000 --port 5000

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Device 2 (192.168.1.101):**
```bash
# Terminal 1: Backend
python start_api.py --api-port 8000 --port 5001

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Connecting:**
- From Device 1: Connect to `192.168.1.101:5001`
- From Device 2: Connect to `192.168.1.100:5000`

## Testing the Connection

1. **Check backend status:**
   - Both devices should show their peer ID in the status panel
   - Active connections should increase after connecting

2. **Send a test message:**
   - Select the connected peer
   - Send a message
   - Verify it appears on the other device

3. **Test file sharing:**
   - Upload a file on Device 1
   - Check if it appears in Device 2's file list
   - Download from Device 2

## Need Help?

See the [Error Troubleshooting Guide](./ERROR_TROUBLESHOOTING.md) for more detailed error explanations and solutions.

