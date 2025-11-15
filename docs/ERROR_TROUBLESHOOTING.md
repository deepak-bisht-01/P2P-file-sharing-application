# Error Troubleshooting Guide

This document explains common errors you may encounter in the P2P file sharing application and how to resolve them.

## Network Errors

### ERR_CONNECTION_REFUSED

**What it means:**
The `ERR_CONNECTION_REFUSED` error occurs when the browser tries to connect to the backend server, but the server is not running or not accepting connections on that port.

**Common causes:**
- **Backend server is not running**: The most common cause - you haven't started `start_api.py`
- **Wrong port**: The frontend is trying to connect to a port that's not in use
- **Server crashed**: The backend server stopped unexpectedly
- **Firewall blocking**: A firewall is blocking the connection (less common for localhost)

**How to fix:**

1. **Start the backend server:**
   ```bash
   # From the project root directory
   python start_api.py --api-port 8000
   ```
   
   You should see:
   ```
   Starting P2P Messaging API server on 0.0.0.0:8000
   P2P peer will listen on port 5000
   ```

2. **Verify the server is running:**
   - Check the terminal where you started the server - it should show "Application startup complete"
   - Test the connection manually:
     ```bash
     # On Windows PowerShell:
     Test-NetConnection -ComputerName localhost -Port 8000
     
     # Or use curl:
     curl http://localhost:8000/api/status
     ```

3. **Check the API URL:**
   - Look at the footer of the web app - it shows the API endpoint
   - If it shows `http://localhost:8000`, make sure the server is running on that port
   - If using a different device, you may need to use the device's IP address instead of `localhost`

4. **For multi-device setup:**
   - Each device needs its own backend server running
   - Or, if accessing from another device, use the server's IP address:
     - Find the server's IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
     - Update `VITE_API_BASE_URL` to use the IP: `http://<server-ip>:8000`
     - Rebuild the frontend: `npm run build`

**Error handling improvements:**
The application now provides clearer error messages:
- "Connection refused: Cannot connect to backend server at http://localhost:8000. Please ensure the backend server is running. Start it with: python start_api.py --api-port 8000"

---

### ERR_NETWORK_CHANGED

**What it means:**
The `ERR_NETWORK_CHANGED` error occurs when the browser detects that the network connection has changed during a request. This can happen when:

1. **Network interface changes**: Your WiFi connection switches, IP address changes, or network adapter is reset
2. **Server becomes unavailable**: The backend server stops running or becomes unreachable
3. **Connection timeout**: The server takes too long to respond
4. **Network instability**: Intermittent network issues

**Common causes:**
- Backend server (`start_api.py`) is not running
- Backend server crashed or stopped
- Network connection was interrupted
- Firewall blocking the connection
- Incorrect API base URL configuration

**How to fix:**

1. **Check if the backend server is running:**
   ```bash
   # Make sure you've started the API server
   python start_api.py --api-port 8000
   ```

2. **Verify the API endpoint:**
   - Check the footer of the web app - it should show the API endpoint
   - Default is `http://localhost:8000`
   - If using a different URL, set `VITE_API_BASE_URL` environment variable

3. **Check network connectivity:**
   - Ensure your network connection is stable
   - If using WiFi, try reconnecting
   - Check firewall settings

4. **Restart the application:**
   - Stop the backend server (Ctrl+C)
   - Restart it: `python start_api.py --api-port 8000`
   - Refresh the browser

**Error handling improvements:**
The application now provides clearer error messages when network errors occur. Instead of just showing "ERR_NETWORK_CHANGED", you'll see messages like:
- "Network error: Unable to connect to server. Please ensure the backend server is running at http://localhost:8000"
- "Network connection changed. Please check your internet connection and ensure the server is still running."

---

## HTTP 400 Bad Request - Peer Connection

**What it means:**
A 400 Bad Request error on `/api/peers/connect` indicates that the connection attempt to another peer failed.

**Common causes:**
1. **Target peer is not running**: The peer you're trying to connect to is not active
2. **Incorrect host/port**: The host address or port number is wrong
3. **Network unreachable**: The target peer is on a different network and not accessible
4. **Firewall blocking**: A firewall is preventing the connection
5. **Connection timeout**: The peer didn't respond within the timeout period (5 seconds)

**How to fix:**

1. **Verify the target peer is running:**
   - Make sure the peer you're connecting to has its backend server running
   - Check that it's listening on the correct port

2. **Check host and port:**
   - For local connections, use `127.0.0.1` or `localhost`
   - For remote connections, use the correct IP address
   - Verify the port number matches the peer's listening port (default: 5000)

3. **Test connectivity:**
   ```bash
   # Test if the peer is reachable (replace with actual IP and port)
   telnet <peer-ip> <peer-port>
   # Or use PowerShell on Windows:
   Test-NetConnection -ComputerName <peer-ip> -Port <peer-port>
   ```

4. **Check firewall settings:**
   - Ensure the peer port (default 5000) is not blocked by firewall
   - On Windows, check Windows Firewall settings
   - On Linux/Mac, check iptables or firewall rules

5. **Verify network configuration:**
   - For local network connections, ensure both peers are on the same network
   - For internet connections, ensure proper port forwarding if behind NAT

**Improved error messages:**
The application now provides more detailed error messages:
- "Failed to connect to peer at 127.0.0.1:5001. Please ensure the peer is running and reachable, and that the host and port are correct."
- "Connection error: [specific error]. Please check that the peer is running and accessible."

**Multi-device scenarios:**
- If connecting from Device 1 to Device 2, make sure:
  1. Device 2's backend server is running
  2. Device 2's peer node is running (on port 5000 or 5001)
  3. You're using Device 2's actual IP address, not `localhost`
  4. Firewall allows connections on the peer port

---

## Multi-Device Setup

When running the application on multiple devices, each device needs proper configuration:

### Setup for Device 1 (Server Device)

1. **Start the backend server:**
   ```bash
   python start_api.py --api-port 8000 --port 5000
   ```

2. **Find the device's IP address:**
   ```bash
   # Windows:
   ipconfig
   # Look for IPv4 Address (e.g., 192.168.1.100)
   
   # Linux/Mac:
   ifconfig
   # or
   ip addr show
   ```

3. **Note the IP address** - you'll need it for Device 2

### Setup for Device 2 (Client Device)

**Option A: Run backend on Device 2 (Recommended)**
- Each device should run its own backend server
- This allows each device to be both a client and a server
- Start the server: `python start_api.py --api-port 8000 --port 5001` (use different port)

**Option B: Connect to Device 1's backend**
- If Device 2 should connect to Device 1's API:
  1. Set environment variable before starting frontend:
     ```bash
     # Windows PowerShell:
     $env:VITE_API_BASE_URL="http://<device1-ip>:8000"
     npm run dev
     
     # Linux/Mac:
     export VITE_API_BASE_URL="http://<device1-ip>:8000"
     npm run dev
     ```
  2. Replace `<device1-ip>` with the actual IP address from Device 1

### Connecting Peers Between Devices

1. **Device 1** should connect to **Device 2's peer port** (default 5000 or 5001)
2. **Device 2** should connect to **Device 1's peer port** (default 5000)
3. Use the actual IP addresses, not `localhost` or `127.0.0.1`
   - Example: Connect to `192.168.1.100:5000` instead of `127.0.0.1:5000`

### Common Multi-Device Issues

**Issue: Connection Refused on Device 2**
- **Solution**: Start the backend server on Device 2, or configure Device 2 to use Device 1's IP address

**Issue: 400 Bad Request when connecting peers**
- **Solution**: 
  - Ensure both devices have their backend servers running
  - Use the correct IP addresses (not localhost)
  - Check that peer ports (5000, 5001) are not blocked by firewall
  - Verify the peer you're connecting to is actually running

**Issue: Can't see peers from other device**
- **Solution**:
  - Make sure both devices are connected to the same network
  - Check firewall settings allow connections on peer ports (5000, 5001)
  - Verify both peers are running and connected

---

## General Troubleshooting Steps

### 1. Check Backend Server Status

```bash
# Start the backend server
python start_api.py --api-port 8000

# You should see:
# Starting P2P Messaging API server on 0.0.0.0:8000
# P2P peer will listen on port 5000
```

### 2. Verify API Endpoint

- Open the browser developer console (F12)
- Check the Network tab for failed requests
- Verify the API base URL matches your server configuration

### 3. Check Logs

- Backend logs: Check the console output from `start_api.py`
- Application logs: Check `logs/p2p_messaging.log` for detailed error information

### 4. Test API Endpoints Manually

```bash
# Test status endpoint
curl http://localhost:8000/api/status

# Test peers endpoint
curl http://localhost:8000/api/peers
```

### 5. Common Configuration Issues

**Wrong API URL:**
- Set `VITE_API_BASE_URL` environment variable before building:
  ```bash
  export VITE_API_BASE_URL=http://localhost:8000
  npm run build
  ```

**Port conflicts:**
- If port 8000 is in use, start with a different port:
  ```bash
  python start_api.py --api-port 8001
  ```
- Update the frontend API base URL accordingly

**CORS issues:**
- The backend is configured to allow all origins
- If you see CORS errors, check the `CORSMiddleware` configuration in `src/backend/api.py`

---

## Error Prevention Tips

1. **Always start the backend server before opening the frontend**
2. **Keep the backend server running while using the application**
3. **Use stable network connections**
4. **Verify peer addresses before connecting**
5. **Check firewall settings for both API port (8000) and peer port (5000)**
6. **Monitor logs for early warning signs of issues**

---

## Getting Help

If you continue to experience issues:

1. Check the browser console for detailed error messages
2. Review backend server logs
3. Verify network connectivity
4. Ensure all required ports are open
5. Check that both peers are running and accessible

