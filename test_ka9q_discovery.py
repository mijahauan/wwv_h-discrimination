#!/usr/bin/env python3
"""
Test ka9q-python discovery directly
"""

from ka9q.discovery import discover_channels

print("Testing ka9q-python discovery...")
print("Listening for 10 seconds...")
print()

channels = discover_channels('bee1-hf-status.local', listen_duration=10.0)

print(f"Found {len(channels)} channels")
print()

if channels:
    print(f"{'SSRC':<12} {'Frequency':<12} {'Preset':<8} {'Rate':<10} {'Multicast':<25}")
    print("-" * 70)
    for ssrc, ch in channels.items():
        freq_str = f"{ch.frequency/1e6:.3f} MHz"
        rate_str = f"{ch.sample_rate} Hz" if ch.sample_rate else "N/A"
        mcast_str = f"{ch.multicast_address}:{ch.port}" if ch.multicast_address else "N/A"
        print(f"{ssrc:<12} {freq_str:<12} {ch.preset:<8} {rate_str:<10} {mcast_str:<25}")
else:
    print("❌ No channels discovered!")
    print()
    print("This means radiod is not broadcasting status packets on multicast,")
    print("or there is a network/firewall issue preventing reception.")
