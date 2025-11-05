#!/usr/bin/env python3
"""
Create WWV/WWVH channels on radiod for discrimination analysis.
Creates 4 IQ channels at 2.5, 5, 10, and 15 MHz with SSRC = frequency in Hz.
"""

import argparse
import sys
from ka9q import RadiodControl
import config

def create_channels(radiod_host):
    """Create WWV/WWVH channels on radiod."""
    print("=" * 70)
    print("Creating WWV/WWVH Channels on Radiod")
    print(f"Radiod: {radiod_host}")
    print("=" * 70)
    
    # Connect to radiod
    print(f"\nConnecting to radiod at {radiod_host}...")
    try:
        control = RadiodControl(radiod_host)
        print("✅ Connected to radiod\n")
    except Exception as e:
        print(f"❌ Failed to connect to radiod: {e}")
        return 1
    
    # Create channel for each frequency
    success_count = 0
    for name, freq_hz in config.FREQUENCIES.items():
        ssrc = config.get_ssrc(freq_hz)
        freq_mhz = freq_hz / 1e6
        
        print(f"Creating {name} channel:")
        print(f"  Frequency: {freq_mhz:.1f} MHz")
        print(f"  SSRC: {ssrc}")
        print(f"  Preset: iq (raw I/Q)")
        print(f"  Sample Rate: {config.SAMPLE_RATE} Hz")
        
        try:
            control.create_and_configure_channel(
                ssrc=ssrc,
                frequency_hz=freq_hz,
                preset='iq',  # Raw I/Q output for analysis
                sample_rate=config.SAMPLE_RATE,
                agc_enable=0,  # Disable AGC for consistent measurements
                gain=0.0       # Manual gain
            )
            print(f"✅ Created {name} channel\n")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to create {name}: {e}\n")
    
    control.close()
    
    print("=" * 70)
    print(f"SUMMARY: Created {success_count}/{len(config.FREQUENCIES)} channels")
    print("=" * 70)
    
    if success_count == len(config.FREQUENCIES):
        print("\n✅ All channels created successfully!")
        print("\nYou can now run:")
        print(f"  python3 main.py --radiod {radiod_host}")
        return 0
    else:
        print("\n⚠️  Some channels failed to create.")
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create WWV/WWVH channels on radiod'
    )
    parser.add_argument(
        '--radiod',
        default='radiod.local',
        help='Radiod hostname or IP address (default: radiod.local)'
    )
    
    args = parser.parse_args()
    
    sys.exit(create_channels(args.radiod))
