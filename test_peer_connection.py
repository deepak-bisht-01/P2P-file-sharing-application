#!/usr/bin/env python3
"""
Diagnostic script to test peer-to-peer connections between devices.
Usage: python test_peer_connection.py <target_host> <target_port>
"""
import sys
import socket
import time

def test_connection(host: str, port: int, timeout: int = 10):
    """Test if a peer connection can be established"""
    print(f"\n{'='*60}")
    print(f"Testing connection to {host}:{port}")
    print(f"{'='*60}\n")
    
    # Test 1: Basic socket connection
    print("Test 1: Basic TCP Connection")
    print("-" * 60)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        print(f"Attempting to connect to {host}:{port}...")
        start_time = time.time()
        sock.connect((host, port))
        elapsed = time.time() - start_time
        print(f"✓ Connection successful! (took {elapsed:.2f} seconds)")
        sock.close()
        return True
    except socket.timeout:
        print(f"✗ Connection timeout after {timeout} seconds")
        print("  Possible causes:")
        print("    - Target peer is not running")
        print("    - Firewall is blocking the connection")
        print("    - Network is unreachable")
        return False
    except ConnectionRefusedError:
        print(f"✗ Connection refused")
        print("  Possible causes:")
        print("    - Target peer is not running on that port")
        print("    - Port number is incorrect")
        return False
    except OSError as e:
        print(f"✗ Connection failed: {e}")
        errno = getattr(e, 'winerror', getattr(e, 'errno', None))
        if errno == 10051:  # Windows: network unreachable
            print("  Network is unreachable - check IP address")
        elif errno == 10060:  # Windows: connection timeout
            print("  Connection timeout - check firewall settings")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_peer_connection.py <target_host> <target_port>")
        print("\nExample:")
        print("  python test_peer_connection.py 192.168.1.100 5000")
        print("  python test_peer_connection.py 192.168.1.101 5001")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    print(f"\nLocal IP Address: {get_local_ip()}")
    print(f"Target: {host}:{port}\n")
    
    success = test_connection(host, port)
    
    if success:
        print("\n" + "="*60)
        print("✓ Connection test PASSED")
        print("="*60)
        print("\nNext steps:")
        print("1. Make sure both devices have their backend servers running")
        print("2. Try connecting from the web interface")
        print("3. Check the peer list after connecting")
    else:
        print("\n" + "="*60)
        print("✗ Connection test FAILED")
        print("="*60)
        print("\nTroubleshooting steps:")
        print("1. Verify the target peer is running:")
        print("   - Check that the backend server is started")
        print("   - Look for 'Peer node started on 0.0.0.0:PORT' in the logs")
        print("\n2. Check firewall settings:")
        print("   - Windows: Allow Python through Windows Firewall")
        print("   - Ensure port", port, "is not blocked")
        print("\n3. Verify network connectivity:")
        print("   - Ensure both devices are on the same network")
        print("   - Ping the target device: ping", host)
        print("\n4. Check IP address:")
        print("   - Use actual IP address (192.168.x.x), not localhost")
        print("   - Verify IP with: ipconfig (Windows) or ifconfig (Linux/Mac)")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

