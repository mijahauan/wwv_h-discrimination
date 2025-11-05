#!/usr/bin/env python3
"""
Diagnostic script to check radiod status and discover channels.
Helps troubleshoot RTP stream configuration.
"""

import sys
import argparse
from ka9q.discovery import discover_channels
from ka9q import RadiodControl
import config

def main():
    parser = argparse.ArgumentParser(
        description='Check radiod status and discover channels'
    )
    parser.add_argument(
        '--radiod',
        default='radiod.local',
        help='Radiod hostname or IP address'
    )
    parser.add_argument(
        '--listen-time',
        type=float,
        default=3.0,
        help='Time to listen for channel discovery (seconds)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"RADIOD DIAGNOSTIC CHECK")
    print(f"Radiod address: {args.radiod}")
    print("=" * 70)
    
    # Step 1: Discover existing channels
    print(f"\n[1] Discovering channels (listening for {args.listen_time} seconds)...")
    try:
        channels = discover_channels(args.radiod, listen_duration=args.listen_time)
        
        if not channels:
            print("❌ NO CHANNELS FOUND")
            print("\nPossible reasons:")
            print("  1. Radiod is not running")
            print("  2. Radiod has no active channels")
            print("  3. Network connectivity issues")
            print("  4. Wrong radiod address")
            print("\nTry:")
            print(f"  - Check if radiod is running: ssh to radiod host and run 'systemctl status radiod'")
            print(f"  - Create a channel manually to test")
            return 1
        
        print(f"✅ Found {len(channels)} channel(s)\n")
        
        # Display channel information
        print(f"{'SSRC':<12} {'Frequency':<12} {'Preset':<8} {'Rate':<10} {'RTP Output':<25} {'SNR':<8}")
        print("-" * 80)
        
        has_rtp_output = False
        rtp_addresses = set()
        
        for ssrc, ch in sorted(channels.items()):
            freq_str = f"{ch.frequency/1e6:.3f} MHz"
            rate_str = f"{ch.sample_rate} Hz" if ch.sample_rate else "N/A"
            
            if ch.multicast_address and ch.port:
                rtp_str = f"{ch.multicast_address}:{ch.port}"
                has_rtp_output = True
                rtp_addresses.add((ch.multicast_address, ch.port))
            else:
                rtp_str = "NO OUTPUT"
            
            snr_str = f"{ch.snr:.1f} dB" if ch.snr > -100 else "N/A"
            
            print(f"{ssrc:<12} {freq_str:<12} {ch.preset:<8} {rate_str:<10} {rtp_str:<25} {snr_str:<8}")
        
        # Step 2: Check RTP output configuration
        print(f"\n[2] RTP Output Status:")
        if has_rtp_output:
            print(f"✅ Channels have RTP output configured")
            print(f"\nRTP Multicast Address(es):")
            for addr, port in sorted(rtp_addresses):
                print(f"  {addr}:{port}")
        else:
            print(f"❌ NO RTP OUTPUT CONFIGURED")
            print("\nThis means radiod is not configured to send RTP data.")
            print("Check radiod.conf for 'data' parameter, e.g.:")
            print("  data = 239.1.2.3:5004")
            return 1
        
        # Step 3: Check for our expected channels
        print(f"\n[3] Checking for WWV/WWVH channels:")
        expected_ssrcs = {config.get_ssrc(freq): name for name, freq in config.FREQUENCIES.items()}
        
        found_count = 0
        for ssrc, name in expected_ssrcs.items():
            if ssrc in channels:
                ch = channels[ssrc]
                print(f"✅ {name:<8} SSRC={ssrc:<6} at {ch.frequency/1e6:.3f} MHz")
                found_count += 1
            else:
                print(f"❌ {name:<8} SSRC={ssrc:<6} NOT FOUND")
        
        if found_count == 0:
            print(f"\nℹ️  No WWV/WWVH channels found yet.")
            print(f"   Run 'python3 main.py --radiod {args.radiod}' to create them")
        elif found_count < len(expected_ssrcs):
            print(f"\nℹ️  Only {found_count}/{len(expected_ssrcs)} channels found.")
            print(f"   Run 'python3 main.py --radiod {args.radiod}' to create missing channels")
        else:
            print(f"\n✅ All {found_count} WWV/WWVH channels are configured!")
        
        # Step 4: Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY:")
        print(f"  Radiod Status: ✅ Online")
        print(f"  Total Channels: {len(channels)}")
        print(f"  RTP Output: {'✅ Configured' if has_rtp_output else '❌ Not configured'}")
        print(f"  WWV/WWVH Channels: {found_count}/{len(expected_ssrcs)}")
        
        if has_rtp_output and found_count == len(expected_ssrcs):
            print(f"\n✅ Ready to run! Execute:")
            print(f"   python3 main.py --radiod {args.radiod}")
        elif not has_rtp_output:
            print(f"\n❌ Radiod needs RTP output configuration.")
            print(f"   Add to radiod.conf: data = 239.1.2.3:5004")
        else:
            print(f"\n⚠️  Some channels missing. The app will create them automatically.")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
