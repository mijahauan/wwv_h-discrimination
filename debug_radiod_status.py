#!/usr/bin/env python3
"""
Debug script to dump raw status packet fields from radiod.
Shows what fields radiod is actually sending.
"""

import sys
import argparse
from ka9q.discovery import discover_channels
from ka9q import RadiodControl
from ka9q.types import StatusType

# Map of status type values to names
STATUS_TYPE_NAMES = {v: k for k, v in vars(StatusType).items() if isinstance(v, int)}

def debug_status_fields(radiod_host, listen_time=3.0):
    """
    Discover channels and show what status fields radiod is sending.
    """
    print("=" * 70)
    print(f"DEBUG: Radiod Status Fields")
    print(f"Radiod: {radiod_host}")
    print("=" * 70)
    
    # Discover channels
    print(f"\n[1] Discovering channels (listening {listen_time}s)...")
    channels = discover_channels(radiod_host, listen_duration=listen_time)
    
    if not channels:
        print("❌ No channels discovered")
        return 1
    
    print(f"✅ Discovered {len(channels)} channels\n")
    
    # Connect to radiod to decode a status packet in detail
    print(f"[2] Connecting to radiod to examine status packets...")
    control = RadiodControl(radiod_host)
    
    try:
        # Listen for a status packet
        import socket
        import struct
        
        # Get status multicast address
        status_sock = control._setup_status_listener()
        status_sock.settimeout(5.0)
        
        print(f"[3] Waiting for status packet...\n")
        
        try:
            buffer, addr = status_sock.recvfrom(8192)
            
            if len(buffer) == 0 or buffer[0] != 0:
                print("❌ Not a status packet")
                return 1
            
            print(f"✅ Received status packet ({len(buffer)} bytes) from {addr}")
            print("\nDecoded Fields:")
            print("-" * 70)
            
            # Decode and show each field
            cp = 1  # Skip packet type
            field_count = 0
            
            while cp < len(buffer):
                if cp >= len(buffer):
                    break
                
                type_val = buffer[cp]
                cp += 1
                
                if type_val == StatusType.EOL:
                    print(f"\n[EOL] End of packet")
                    break
                
                if cp >= len(buffer):
                    break
                
                optlen = buffer[cp]
                cp += 1
                
                # Handle extended length
                if optlen & 0x80:
                    length_of_length = optlen & 0x7f
                    optlen = 0
                    for _ in range(length_of_length):
                        if cp >= len(buffer):
                            break
                        optlen = (optlen << 8) | buffer[cp]
                        cp += 1
                
                if cp + optlen > len(buffer):
                    break
                
                data = buffer[cp:cp + optlen]
                
                # Get field name
                field_name = STATUS_TYPE_NAMES.get(type_val, f"UNKNOWN({type_val})")
                
                # Show field
                field_count += 1
                print(f"{field_count:3}. Type {type_val:3} ({field_name:<30}) Length: {optlen:3} bytes")
                
                # Decode specific important fields
                if type_val == StatusType.OUTPUT_DATA_DEST_SOCKET:
                    from ka9q.control import decode_socket
                    sock_info = decode_socket(data, optlen)
                    print(f"     → {sock_info}")
                elif type_val == StatusType.OUTPUT_SSRC:
                    from ka9q.control import decode_int32
                    ssrc = decode_int32(data, optlen)
                    print(f"     → SSRC: {ssrc}")
                elif type_val == StatusType.RADIO_FREQUENCY:
                    from ka9q.control import decode_double
                    freq = decode_double(data, optlen)
                    print(f"     → {freq/1e6:.6f} MHz")
                elif type_val == StatusType.PRESET:
                    from ka9q.control import decode_string
                    preset = decode_string(data, optlen)
                    print(f"     → '{preset}'")
                elif type_val == StatusType.OUTPUT_SAMPRATE:
                    from ka9q.control import decode_int
                    rate = decode_int(data, optlen)
                    print(f"     → {rate} Hz")
                
                cp += optlen
            
            print(f"\n{'='*70}")
            print(f"Total fields in packet: {field_count}")
            print(f"{'='*70}\n")
            
            # Check if OUTPUT_DATA_DEST_SOCKET was present
            status = control._decode_status_response(buffer)
            if 'destination' in status:
                print("✅ OUTPUT_DATA_DEST_SOCKET field IS present")
                print(f"   Destination: {status['destination']}")
            else:
                print("❌ OUTPUT_DATA_DEST_SOCKET field NOT present in status packet")
                print("\nThis means radiod is not configured to send RTP data.")
                print("You need to configure radiod with a 'data' output destination.")
                print("\nExample radiod.conf configuration:")
                print("  [global]")
                print("  data = 239.1.2.3:5004")
                
        except socket.timeout:
            print("❌ Timeout waiting for status packet")
            return 1
            
    finally:
        control.close()
    
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Debug radiod status packet fields'
    )
    parser.add_argument(
        '--radiod',
        default='radiod.local',
        help='Radiod hostname or IP'
    )
    parser.add_argument(
        '--listen-time',
        type=float,
        default=3.0,
        help='Listen duration for discovery'
    )
    
    args = parser.parse_args()
    
    sys.exit(debug_status_fields(args.radiod, args.listen_time))
