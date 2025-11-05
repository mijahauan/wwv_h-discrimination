#!/usr/bin/env python3
"""
Test multicast reception to diagnose discovery issues
"""

import socket
import struct
import time
import sys

def test_multicast_detailed(mcast_addr, port=5006, duration=10.0):
    """Detailed test of multicast reception"""
    
    print(f"=" * 70)
    print(f"Testing Multicast Reception")
    print(f"=" * 70)
    print(f"Multicast Address: {mcast_addr}")
    print(f"Port: {port}")
    print(f"Duration: {duration} seconds")
    print()
    
    # Step 1: Create socket
    print("[1] Creating UDP socket...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("  ✓ Socket created")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    # Step 2: Set socket options
    print("[2] Setting socket options...")
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("  ✓ SO_REUSEADDR enabled")
        
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                print("  ✓ SO_REUSEPORT enabled")
            except:
                print("  ⚠ SO_REUSEPORT not available")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        sock.close()
        return False
    
    # Step 3: Bind to port
    print(f"[3] Binding to port {port}...")
    try:
        sock.bind(('', port))
        print(f"  ✓ Bound to 0.0.0.0:{port}")
    except Exception as e:
        print(f"  ✗ Failed to bind: {e}")
        print(f"     Port {port} may already be in use")
        sock.close()
        return False
    
    # Step 4: Join multicast group
    print(f"[4] Joining multicast group {mcast_addr}...")
    try:
        mreq = struct.pack('=4s4s',
                          socket.inet_aton(mcast_addr),
                          socket.inet_aton('0.0.0.0'))  # Any interface
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print(f"  ✓ Joined multicast group on all interfaces")
    except Exception as e:
        print(f"  ✗ Failed to join multicast group: {e}")
        sock.close()
        return False
    
    # Step 5: Set timeout
    sock.settimeout(0.5)
    print(f"  ✓ Socket configured")
    print()
    
    # Step 6: Listen for packets
    print(f"[5] Listening for packets (up to {duration} seconds)...")
    print("=" * 70)
    
    start_time = time.time()
    packet_count = 0
    total_bytes = 0
    
    while time.time() - start_time < duration:
        try:
            data, addr = sock.recvfrom(8192)
            packet_count += 1
            total_bytes += len(data)
            
            # Parse packet type (first byte)
            pkt_type = data[0] if data else -1
            type_str = {0: 'STATUS', 1: 'COMMAND'}.get(pkt_type, f'UNKNOWN({pkt_type})')
            
            elapsed = time.time() - start_time
            print(f"  [{elapsed:5.1f}s] Packet #{packet_count}: {len(data):5d} bytes from {addr[0]}:{addr[1]:5d} type={type_str}")
            
        except socket.timeout:
            # No packet received in this interval
            pass
        except Exception as e:
            print(f"  ✗ Error receiving: {e}")
    
    sock.close()
    
    print("=" * 70)
    print(f"Results:")
    print(f"  Packets received: {packet_count}")
    print(f"  Total bytes: {total_bytes:,}")
    print(f"  Listen duration: {time.time() - start_time:.1f} seconds")
    print()
    
    if packet_count > 0:
        print("✓ SUCCESS: Multicast reception is working!")
        return True
    else:
        print("✗ FAILED: No packets received")
        print()
        print("Troubleshooting:")
        print("  1. Check if radiod is running and has active channels")
        print("  2. Verify radiod is sending status updates (check radiod logs)")
        print("  3. Check firewall settings (may be blocking multicast)")
        print("  4. Verify network routing (multicast may not route)")
        print("  5. Try on radiod host itself to confirm packets are sent")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_multicast.py <multicast_address> [port]")
        print()
        print("Example:")
        print("  python3 test_multicast.py 239.251.200.193 5006")
        sys.exit(1)
    
    mcast_addr = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5006
    
    success = test_multicast_detailed(mcast_addr, port, duration=10.0)
    sys.exit(0 if success else 1)
