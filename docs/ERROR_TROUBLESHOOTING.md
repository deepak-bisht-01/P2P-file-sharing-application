# Error Troubleshooting Guide

This document explains common errors you may encounter in the P2P file sharing application and how to resolve them.

## Network Errors

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

