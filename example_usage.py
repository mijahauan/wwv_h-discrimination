#!/usr/bin/env python3
"""
Example usage and testing script for WWV/WWVH discrimination application.
This demonstrates how to use the various components.
"""

import logging
import time
from datetime import datetime

from stream_receiver import MultiFrequencyReceiver
from time_domain import MultiFrequencyTimeDomainAnalyzer
from freq_domain import MultiFrequencyFreqDomainAnalyzer
from data_logger import DataLogger
import config


def example_basic_usage():
    """
    Basic example: Connect and run for a short time.
    """
    print("=" * 80)
    print("Example: Basic Usage")
    print("=" * 80)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize receiver
    receiver = MultiFrequencyReceiver(radiod_host='radiod.local')
    
    try:
        # Connect and create channels
        receiver.connect()
        
        # Start receiving
        receiver.start_receivers()
        
        print("Waiting for data...")
        time.sleep(10)
        
        # Check receiver statistics
        stats = receiver.get_all_statistics()
        print("\nReceiver Statistics:")
        for freq, stat in stats.items():
            print(f"{freq}: {stat['packets_received']} packets, "
                  f"{stat['samples_received']} samples")
        
        # Shutdown
        receiver.shutdown()
        print("\nExample complete!")
    
    except Exception as e:
        print(f"Error: {e}")
        receiver.shutdown()


def example_time_domain():
    """
    Example: Time-domain analysis only.
    """
    print("=" * 80)
    print("Example: Time-Domain Analysis")
    print("=" * 80)
    
    logging.basicConfig(level=logging.INFO)
    
    receiver = MultiFrequencyReceiver(radiod_host='radiod.local')
    
    try:
        receiver.connect()
        receiver.start_receivers()
        
        # Initialize time-domain analyzer
        td_analyzer = MultiFrequencyTimeDomainAnalyzer(receiver)
        
        print("Running time-domain analysis...")
        print("Waiting for minute 1 (WWVH) or minute 2 (WWV)...")
        
        # Run for a few cycles
        for _ in range(10):
            results = td_analyzer.run_measurement_cycle()
            
            if results:
                print("\nMeasurements taken:")
                for freq, result in results.items():
                    print(f"  {freq} - {result['station'].upper()}: "
                          f"RSSI={result['rssi_dbm']:.1f} dBm, "
                          f"SNR={result['snr_db']:.1f} dB")
            
            time.sleep(5)
        
        # Show statistics
        stats = td_analyzer.get_all_statistics()
        print("\n\nStatistics:")
        for freq, stat in stats.items():
            print(f"\n{freq}:")
            if stat['wwv']['count'] > 0:
                print(f"  WWV: {stat['wwv']['count']} measurements, "
                      f"mean RSSI = {stat['wwv']['mean_rssi']:.1f} dBm")
            if stat['wwvh']['count'] > 0:
                print(f"  WWVH: {stat['wwvh']['count']} measurements, "
                      f"mean RSSI = {stat['wwvh']['mean_rssi']:.1f} dBm")
        
        receiver.shutdown()
        print("\nExample complete!")
    
    except Exception as e:
        print(f"Error: {e}")
        receiver.shutdown()


def example_freq_domain():
    """
    Example: Frequency-domain analysis only.
    """
    print("=" * 80)
    print("Example: Frequency-Domain Analysis")
    print("=" * 80)
    
    logging.basicConfig(level=logging.INFO)
    
    receiver = MultiFrequencyReceiver(radiod_host='radiod.local')
    
    try:
        receiver.connect()
        receiver.start_receivers()
        
        # Initialize frequency-domain analyzer
        fd_analyzer = MultiFrequencyFreqDomainAnalyzer(receiver)
        
        print("Running frequency-domain analysis...")
        print("Waiting for minute markers (1000 Hz WWV, 1200 Hz WWVH)...")
        
        # Run for several minutes
        measurements_taken = 0
        for _ in range(300):  # 5 minutes
            results = fd_analyzer.run_measurement_cycle()
            
            if results:
                measurements_taken += 1
                print(f"\nMeasurement #{measurements_taken}:")
                for freq, result in results.items():
                    print(f"  {freq}:")
                    print(f"    WWV (1000 Hz): {result['wwv_power_db']:.1f} dB "
                          f"[{'detected' if result['wwv_detected'] else 'absent'}]")
                    print(f"    WWVH (1200 Hz): {result['wwvh_power_db']:.1f} dB "
                          f"[{'detected' if result['wwvh_detected'] else 'absent'}]")
                    if result['ratio_db']:
                        print(f"    Ratio: {result['ratio_db']:+.1f} dB")
            
            time.sleep(1)
        
        # Show statistics
        stats = fd_analyzer.get_all_statistics()
        print("\n\nStatistics:")
        for freq, stat in stats.items():
            print(f"\n{freq}:")
            print(f"  Measurements: {stat['count']}")
            if stat['count'] > 0:
                print(f"  WWV detection rate: {stat['wwv_detection_rate']*100:.1f}%")
                print(f"  WWVH detection rate: {stat['wwvh_detection_rate']*100:.1f}%")
                if stat.get('mean_ratio'):
                    print(f"  Mean ratio: {stat['mean_ratio']:+.1f} dB")
        
        receiver.shutdown()
        print("\nExample complete!")
    
    except Exception as e:
        print(f"Error: {e}")
        receiver.shutdown()


def example_data_logging():
    """
    Example: Full system with data logging.
    """
    print("=" * 80)
    print("Example: Full System with Data Logging")
    print("=" * 80)
    
    logging.basicConfig(level=logging.INFO)
    
    receiver = MultiFrequencyReceiver(radiod_host='radiod.local')
    data_logger = DataLogger(output_dir='example_data')
    
    try:
        receiver.connect()
        receiver.start_receivers()
        
        td_analyzer = MultiFrequencyTimeDomainAnalyzer(receiver)
        fd_analyzer = MultiFrequencyFreqDomainAnalyzer(receiver)
        
        print("Running full analysis with logging...")
        print("Data will be saved to 'example_data' directory")
        
        # Run for a limited time
        start_time = time.time()
        duration = 300  # 5 minutes
        
        while time.time() - start_time < duration:
            # Time-domain
            td_results = td_analyzer.run_measurement_cycle()
            for freq, result in td_results.items():
                data_logger.log_time_domain_measurement(freq, result)
                print(f"[TD] {freq} - {result['station'].upper()}: "
                      f"{result['rssi_dbm']:.1f} dBm")
            
            # Frequency-domain
            fd_results = fd_analyzer.run_measurement_cycle()
            for freq, result in fd_results.items():
                data_logger.log_freq_domain_measurement(freq, result)
                print(f"[FD] {freq} - Ratio: {result['ratio_db']:+.1f} dB")
            
            time.sleep(1)
        
        receiver.shutdown()
        print("\nExample complete! Check 'example_data' directory for logs.")
    
    except Exception as e:
        print(f"Error: {e}")
        receiver.shutdown()


if __name__ == '__main__':
    import sys
    
    print("WWV/WWVH Discrimination - Example Usage\n")
    print("Choose an example:")
    print("1. Basic usage (connect and check receivers)")
    print("2. Time-domain analysis")
    print("3. Frequency-domain analysis")
    print("4. Full system with data logging")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        example_basic_usage()
    elif choice == '2':
        example_time_domain()
    elif choice == '3':
        example_freq_domain()
    elif choice == '4':
        example_data_logging()
    else:
        print("Invalid choice!")
        sys.exit(1)
