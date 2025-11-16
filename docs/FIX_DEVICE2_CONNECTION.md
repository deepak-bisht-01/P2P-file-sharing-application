# Fix Device 2 Connection Refused Error

## Problem

Device 2's frontend is trying to connect to port **8000**, but Device 2's backend is running on port **8001**.

**Error**: `ERR_CONNECTION_REFUSED` on `:8000/api/*`

## Solution

Set the `VITE_API_BASE_URL` environment variable to point to port **8001** before starting Device 2's frontend.

## Quick Fix

### Step 1: Stop Device 2 Frontend

If it's running, stop it (Ctrl+C in the terminal).

### Step 2: Set Environment Variable and Start

**In PowerShell (Device 2 Frontend terminal):**

```powershell
cd frontend
$env:VITE_API_BASE_URL="http://localhost:8001"
npm run dev
```

### Step 3: Verify

1. Check the browser footer - it should show: `API endpoint: http://localhost:8001`
2. Errors should disappear
3. Status should load correctly

## Alternative: Use the PowerShell Script

I've created `start_device2.ps1` which does this automatically:

```powershell
.\start_device2.ps1
```

This script:
- Starts Device 2 backend on port 8001
- Sets `VITE_API_BASE_URL=http://localhost:8001`
- Starts Device 2 frontend

## Manual Setup (Step by Step)

### Device 2 Backend Terminal:
```powershell
python start_api.py --api-port 8001 --port 5001
```

### Device 2 Frontend Terminal:
```powershell
cd frontend
$env:VITE_API_BASE_URL="http://localhost:8001"
npm run dev
```

## Verify It's Working

1. **Check browser footer**: Should show `http://localhost:8001`
2. **No more errors**: Console should be clean
3. **Status loads**: Network Status panel should show data
4. **Peers list works**: Should be able to see and connect to peers

## Port Summary

| Device | API Port | Peer Port | Frontend Port |
|--------|----------|-----------|---------------|
| Device 1 | 8000 | 5000 | 5173 |
| Device 2 | **8001** | 5001 | 5174 |

## Important Notes

- **Environment variable must be set BEFORE starting `npm run dev`**
- If you restart the frontend, you need to set the variable again
- The variable only affects the current terminal session
- Check the browser footer to confirm which API it's using

## Troubleshooting

### Still seeing errors on port 8000?

1. **Hard refresh the browser**: Ctrl+Shift+R or Ctrl+F5
2. **Check the footer**: Should show port 8001
3. **Restart frontend**: Stop and start again with the environment variable set

### Environment variable not working?

Try this alternative:
```powershell
# Set it and run in one command
$env:VITE_API_BASE_URL="http://localhost:8001"; npm run dev
```

### Want to make it permanent?

Create a `.env` file in the `frontend/` directory:
```
VITE_API_BASE_URL=http://localhost:8001
```

But this would affect both devices, so it's better to use the environment variable method.




