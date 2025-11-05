#!/usr/bin/env python3
"""
Discover radiod instances on the network using mDNS
"""

import subprocess
import re
import sys
import time

def discover_radiod_macos():
    """Discover radiod services using dns-sd (macOS)"""
    print("Discovering radiod services on network...")
    print("Searching for _ka9q-ctl._udp services...")
    print("(Press Ctrl+C to stop after seeing results)")
    print()
    
    try:
        # Browse for ka9q control services
        # dns-sd runs continuously, so we'll let it run for a bit then stop
        proc = subprocess.Popen(
            ['dns-sd', '-B', '_ka9q-ctl._udp', 'local.'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        found_services = []
        
        # Give it 5 seconds to find services
        timeout = time.time() + 5
        while time.time() < timeout:
            line = proc.stdout.readline()
            if line:
                print(line.strip())
                # Look for Add lines
                if 'Add' in line:
                    match = re.search(r'Add.*\s+(\S+)\s+_ka9q-ctl._udp', line)
                    if match:
                        service_name = match.group(1)
                        if service_name not in found_services:
                            found_services.append(service_name)
        
        proc.terminate()
        
        print()
        print(f"Found {len(found_services)} radiod service(s)")
        
        if found_services:
            print()
            print("To use with this app, specify:")
            for svc in found_services:
                print(f"  --radiod {svc}.local")
        
        return found_services
        
    except FileNotFoundError:
        print("❌ dns-sd not found (should be available on macOS)")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == '__main__':
    services = discover_radiod_macos()
    sys.exit(0 if services else 1)
