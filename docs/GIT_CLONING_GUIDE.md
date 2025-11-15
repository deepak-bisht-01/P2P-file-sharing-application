# Git Cloning Guide for Multi-Device Setup

## ✅ Yes, You Can Clone from GitHub!

Cloning the repository on Device 2 is **perfectly fine** and **recommended**. The codebase is designed to work this way.

## What's Already Protected

Your `.gitignore` file already excludes device-specific files:

```
peer_identity.json      ✅ Ignored
identity_*.json         ✅ Ignored
logs/                    ✅ Ignored
downloads/               ✅ Ignored
shared_files/            ✅ Ignored
```

## Important: Remove peer_identity.json from Git (If Already Committed)

If `peer_identity.json` was committed to git **before** it was added to `.gitignore`, you need to remove it from git tracking:

### On Device 1 (Before Pushing to GitHub)

```bash
# Remove from git tracking (but keep the local file)
git rm --cached peer_identity.json

# Commit the removal
git commit -m "Remove peer_identity.json from git tracking"

# Push to GitHub
git push
```

### Verify It's Ignored

```bash
# Check if it's still tracked
git ls-files | grep peer_identity.json

# If nothing is returned, it's properly ignored ✅
```

## Device 2 Setup After Cloning

### Step 1: Clone the Repository

```bash
git clone <your-github-repo-url>
cd P2P-file-sharing-application
```

### Step 2: Install Dependencies

**Python dependencies:**
```bash
pip install -r requirements.txt
```

**Node.js dependencies:**
```bash
cd frontend
npm install
cd ..
```

### Step 3: Start the Application

```bash
# Backend (will auto-create peer_identity.json)
python start_api.py --api-port 8000 --port 5001

# Frontend (in another terminal)
cd frontend
npm run dev
```

### Step 4: Verify Identity Creation

When you start the backend on Device 2, it will **automatically**:
1. Check if `peer_identity.json` exists
2. If not found, create a **new unique identity** for Device 2
3. Generate a unique peer ID and RSA key pair

**You'll see in the logs:**
```
Peer ID: <unique-device2-peer-id>
```

## What Happens Automatically

### Device 1 (Original)
- Has its own `peer_identity.json` (not in git)
- Unique peer ID: `1f0c84f2-f2b3-4c3a-835f-b90f6d265c44-...`

### Device 2 (Cloned)
- Will create its own `peer_identity.json` on first run
- Unique peer ID: `<different-uuid>-<different-hash>`
- **Completely independent** from Device 1

## Files That Are Safe to Share via Git

✅ **Safe to commit:**
- All source code (`src/`, `frontend/src/`)
- Configuration files (`config/`, `*.yaml`)
- Documentation (`docs/`, `README.md`)
- Build scripts (`start_api.py`, `setup.py`)
- Dependency files (`requirements.txt`, `package.json`)

❌ **Never commit:**
- `peer_identity.json` (device-specific identity)
- `logs/` (runtime logs)
- `downloads/` (downloaded files)
- `shared_files/` (shared files)
- `__pycache__/` (Python cache)
- `node_modules/` (Node.js dependencies)

## Troubleshooting

### Issue: Device 2 has same peer ID as Device 1

**Problem:** `peer_identity.json` was committed to git and cloned.

**Solution:**
1. Delete `peer_identity.json` on Device 2:
   ```bash
   rm peer_identity.json
   ```
2. Restart the backend - it will create a new identity
3. Remove from git tracking on Device 1 (see above)

### Issue: Git shows peer_identity.json as modified

**Problem:** File exists locally but git is tracking it.

**Solution:**
```bash
# Remove from tracking
git rm --cached peer_identity.json

# Add to .gitignore (already there, but verify)
echo "peer_identity.json" >> .gitignore

# Commit
git commit -m "Stop tracking peer_identity.json"
```

### Issue: Can't connect after cloning

**Problem:** Both devices might have same identity (if file was committed).

**Solution:**
1. Delete `peer_identity.json` on Device 2
2. Restart Device 2's backend
3. Verify Device 2 has a different peer ID
4. Connect again

## Best Practices

1. **Always check `.gitignore`** before committing
2. **Never commit** `peer_identity.json`
3. **Each device** should have its own unique identity
4. **Clone fresh** on each device for clean setup
5. **Verify identities** are different before connecting

## Verification Checklist

After cloning on Device 2:

- [ ] `peer_identity.json` is **NOT** in the cloned repo
- [ ] Backend starts successfully
- [ ] New `peer_identity.json` is created automatically
- [ ] Device 2 has a **different** peer ID than Device 1
- [ ] Both devices can connect to each other
- [ ] Messages work between devices

## Summary

✅ **Cloning is safe** - `.gitignore` protects device-specific files  
✅ **Auto-generation works** - Device 2 creates its own identity  
✅ **No manual setup needed** - Just clone and run  
⚠️ **Remove from git** - If `peer_identity.json` was already committed  

The application is designed to work perfectly with git cloning - each device gets its own unique identity automatically!

