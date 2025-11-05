#!/usr/bin/env python3
"""
Test radiod discovery and connection
"""

import sys
import socket
import struct
import time
import select

def test_multicast_listen(mcast_addr, port=5006, duration=5.0):
    """Test if we can receive multicast packets from radiod status"""
    
    print(f"Testing multicast reception from {mcast_addr}:{port}")
    print(f"Listening for {duration} seconds...")
    print("-" * 60)
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to port
    try:
        sock.bind(('', port))
        print(f"✓ Bound to port {port}")
    except Exception as e:
        print(f"✗ Failed to bind to port {port}: {e}")
        return False
    
    # Join multicast group
    try:
        mreq = struct.pack('=4s4s',
                          socket.inet_aton(mcast_addr),
                          socket.inet_aton('0.0.0.0'))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print(f"✓ Joined multicast group {mcast_addr}")
    except Exception as e:
        print(f"✗ Failed to join multicast group: {e}")
        sock.close()
        return False
    
    sock.settimeout(0.1)
    
    # Listen for packets
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        ready = select.select([sock], [], [], 0.5)
        if ready[0]:
            try:
                data, addr = sock.recvfrom(8192)
                packet_count += 1
                print(f"✓ Packet {packet_count}: {len(data)} bytes from {addr[0]}:{addr[1]}, type={data[0] if data else '?'}")
            except socket.timeout:
                pass
            except Exception as e:
                print(f"  Error receiving: {e}")
    
    sock.close()
    
    print("-" * 60)
    if packet_count > 0:
        print(f"✓ SUCCESS: Received {packet_count} packets")
        return True
    else:
        print(f"✗ FAILED: No packets received")
        print("\nPossible issues:")
        print("  1. Radiod is not running")
        print("  2. Radiod has no active channels")
        print("  3. Network/firewall blocking multicast")
        print("  4. Wrong multicast address")
        return False


def test_radiod_connection(hostname):
    """Test basic connection to radiod"""
    
    print(f"\n{'=' * 60}")
    print(f"Testing radiod at {hostname}")
    print(f"{'=' * 60}\n")
    
    # Step 1: Resolve hostname
    print(f"[1] Resolving {hostname}...")
    try:
        import subprocess
        
        # Try dns-sd (macOS)
        result = subprocess.run(
            ['dns-sd', '-G', 'v4', hostname],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            import re
            for line in result.stdout.split('\n'):
                if hostname in line and re.search(r'\d+\.\d+\.\d+\.\d+', line):
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        mcast_addr = match.group(1)
                        print(f"✓ Resolved to {mcast_addr}")
                        
                        # Step 2: Test multicast listening
                        print(f"\n[2] Testing multicast reception...")
                        success = test_multicast_listen(mcast_addr, 5006, 5.0)
                        
                        return success
        
        print(f"✗ Could not resolve {hostname}")
        return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    hostname = sys.argv[1] if len(sys.argv) > 1 else 'bee1-hf-status.local'
    success = test_radiod_connection(hostname)
    sys.exit(0 if success else 1)
