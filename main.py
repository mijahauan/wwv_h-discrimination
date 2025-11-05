#!/usr/bin/env python3
"""
Main application for WWV/WWVH discrimination.
Monitors 4 frequencies and applies both time-domain and frequency-domain analysis.
"""

import argparse
import logging
import signal
import sys
import time
import os
from datetime import datetime, timedelta

from stream_receiver import MultiFrequencyReceiver
from time_domain import MultiFrequencyTimeDomainAnalyzer
from freq_domain import MultiFrequencyFreqDomainAnalyzer
from data_logger import DataLogger, ReportGenerator
import config

# Import visualization for 24-hour summary
try:
    from visualize import plot_24hour_summary, load_time_domain_data, load_freq_domain_data
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logging.warning("Visualization not available - matplotlib may not be installed")


# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global running
    logger.info("Shutdown signal received, stopping...")
    running = False


def setup_logging(log_level='INFO'):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def display_status(td_analyzer, fd_analyzer, multi_receiver):
    """
    Display current status information.
    
    Args:
        td_analyzer: Time-domain analyzer instance
        fd_analyzer: Frequency-domain analyzer instance
        multi_receiver: Multi-frequency receiver instance
    """
    print("\n" + "=" * 80)
    print(f"WWV/WWVH Discrimination Status - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # Receiver statistics
    print("\nReceiver Statistics:")
    print("-" * 80)
    receiver_stats = multi_receiver.get_all_statistics()
    for freq_name, stats in receiver_stats.items():
        print(f"\n{freq_name} ({config.FREQUENCIES[freq_name]/1e6:.1f} MHz):")
        print(f"  Packets received: {stats['packets_received']}")
        print(f"  Samples received: {stats['samples_received']}")
        print(f"  Packet loss: {stats['packet_loss_count']}")
        print(f"  Buffer fill: {stats['buffer_fill']*100:.1f}%")
    
    # Time-domain statistics
    print("\n\nTime-Domain Analysis (Absolute Carrier Strength):")
    print("-" * 80)
    td_stats = td_analyzer.get_all_statistics()
    for freq_name, stats in td_stats.items():
        print(f"\n{freq_name}:")
        
        if stats['wwv']['count'] > 0:
            print(f"  WWV: {stats['wwv']['count']} measurements")
            print(f"    Mean RSSI: {stats['wwv']['mean_rssi']:.1f} dBm")
            print(f"    Mean SNR: {stats['wwv']['mean_snr']:.1f} dB")
        else:
            print(f"  WWV: No measurements yet")
        
        if stats['wwvh']['count'] > 0:
            print(f"  WWVH: {stats['wwvh']['count']} measurements")
            print(f"    Mean RSSI: {stats['wwvh']['mean_rssi']:.1f} dBm")
            print(f"    Mean SNR: {stats['wwvh']['mean_snr']:.1f} dB")
        else:
            print(f"  WWVH: No measurements yet")
    
    # Discrimination ratios (time-domain)
    print("\nTime-Domain Discrimination Ratios:")
    td_ratios = td_analyzer.get_discrimination_ratios()
    for freq_name, ratio in td_ratios.items():
        print(f"  {freq_name}: {ratio:+.1f} dB {'(WWV stronger)' if ratio > 0 else '(WWVH stronger)'}")
    
    # Frequency-domain statistics
    print("\n\nFrequency-Domain Analysis (Marker Tones):")
    print("-" * 80)
    fd_stats = fd_analyzer.get_all_statistics()
    for freq_name, stats in fd_stats.items():
        print(f"\n{freq_name}:")
        print(f"  Measurements: {stats['count']}")
        
        if stats['count'] > 0:
            print(f"  WWV detection rate: {stats['wwv_detection_rate']*100:.1f}%")
            print(f"  WWVH detection rate: {stats['wwvh_detection_rate']*100:.1f}%")
            
            if stats.get('mean_ratio') is not None:
                print(f"  Mean ratio: {stats['mean_ratio']:+.1f} dB")
    
    # Discrimination ratios (freq-domain)
    print("\nFrequency-Domain Discrimination Ratios:")
    fd_ratios = fd_analyzer.get_discrimination_ratios()
    for freq_name, ratio in fd_ratios.items():
        print(f"  {freq_name}: {ratio:+.1f} dB {'(WWV stronger)' if ratio > 0 else '(WWVH stronger)'}")
    
    print("\n" + "=" * 80 + "\n")


def main():
    """Main application entry point."""
    global running, logger
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='WWV/WWVH Discrimination Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --radiod radiod.local
  %(prog)s --radiod 192.168.1.100 --output-dir /data/wwv --log-level DEBUG
  %(prog)s --radiod radiod.local --multicast 239.1.2.3 --base-port 5004
        """
    )
    
    parser.add_argument(
        '--radiod',
        default=config.RADIOD['default_host'],
        help=f"Radiod hostname or IP (default: {config.RADIOD['default_host']})"
    )
    
    parser.add_argument(
        '--multicast',
        default=None,
        help='Multicast group for RTP streams (if not specified, will auto-discover)'
    )
    
    parser.add_argument(
        '--rtp-port',
        type=int,
        default=None,
        help='RTP data port (if not specified, will auto-discover)'
    )
    
    parser.add_argument(
        '--base-port',
        type=int,
        default=5004,
        help='[DEPRECATED] Use --rtp-port instead'
    )
    
    parser.add_argument(
        '--output-dir',
        default=config.LOGGING['output_dir'],
        help=f"Output directory for logs (default: {config.LOGGING['output_dir']})"
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--status-interval',
        type=int,
        default=300,
        help='Status display interval in seconds (default: 300)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 80)
    logger.info("WWV/WWVH Discrimination Application Starting")
    logger.info("=" * 80)
    logger.info(f"Radiod host: {args.radiod}")
    if args.multicast and args.rtp_port:
        logger.info(f"RTP data address (manual): {args.multicast}:{args.rtp_port}")
    else:
        logger.info(f"RTP data address: Will auto-discover from radiod")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Monitoring frequencies: {', '.join([f'{f/1e6:.1f} MHz' for f in config.FREQUENCIES.values()])}")
    
    # Initialize data logger
    data_logger = DataLogger(output_dir=args.output_dir)
    
    # Save session info
    session_info = {
        'start_time': datetime.utcnow().isoformat(),
        'radiod_host': args.radiod,
        'multicast_group': args.multicast,
        'rtp_port': args.rtp_port,
        'frequencies': {name: freq for name, freq in config.FREQUENCIES.items()},
        'sample_rate': config.SAMPLE_RATE,
        'time_domain_config': config.TIME_DOMAIN,
        'freq_domain_config': config.FREQ_DOMAIN,
    }
    data_logger.save_session_info(session_info)
    
    # Initialize receiver
    logger.info("Initializing multi-frequency receiver...")
    multi_receiver = MultiFrequencyReceiver(radiod_host=args.radiod)
    
    try:
        # Connect to radiod and create channels
        multi_receiver.connect()
        
        # Start RTP receivers
        logger.info("Starting RTP receivers...")
        # Use manual address if provided, otherwise auto-discover
        if args.multicast and args.rtp_port:
            multi_receiver.start_receivers(multicast_group=args.multicast, port=args.rtp_port)
        else:
            multi_receiver.start_receivers()
        
        logger.info("Receivers started, waiting for data...")
        time.sleep(5)  # Wait for initial data
        
        # Initialize analyzers
        logger.info("Initializing analyzers...")
        td_analyzer = MultiFrequencyTimeDomainAnalyzer(multi_receiver)
        fd_analyzer = MultiFrequencyFreqDomainAnalyzer(multi_receiver)
        
        # Create report generator
        report_gen = ReportGenerator(data_logger)
        
        logger.info("Starting measurement loop...")
        logger.info("Press Ctrl+C to stop")
        
        last_status_time = time.time()
        last_summary_time = time.time()
        start_time = datetime.utcnow()
        measurement_cycle = 0
        summary_count = 0
        
        # Main measurement loop
        while running:
            measurement_cycle += 1
            
            try:
                # Run time-domain measurements
                td_results = td_analyzer.run_measurement_cycle()
                for freq_name, result in td_results.items():
                    data_logger.log_time_domain_measurement(freq_name, result)
                
                # Run frequency-domain measurements
                fd_results = fd_analyzer.run_measurement_cycle()
                for freq_name, result in fd_results.items():
                    data_logger.log_freq_domain_measurement(freq_name, result)
                
                # Log statistics periodically
                if measurement_cycle % 60 == 0:  # Every 60 cycles
                    td_stats = td_analyzer.get_all_statistics()
                    for freq_name, stats in td_stats.items():
                        data_logger.log_statistics(freq_name, 'time_domain', stats['wwv'])
                        data_logger.log_statistics(freq_name, 'time_domain', stats['wwvh'])
                    
                    fd_stats = fd_analyzer.get_all_statistics()
                    for freq_name, stats in fd_stats.items():
                        data_logger.log_statistics(freq_name, 'freq_domain', stats)
                
                # Display status periodically
                current_time = time.time()
                if current_time - last_status_time >= args.status_interval:
                    display_status(td_analyzer, fd_analyzer, multi_receiver)
                    last_status_time = current_time
                
                # Generate 24-hour summary if enabled and interval has passed
                if config.LOGGING['generate_24h_summary'] and VISUALIZATION_AVAILABLE:
                    hours_elapsed = (current_time - last_summary_time) / 3600
                    if hours_elapsed >= config.LOGGING['summary_interval_hours']:
                        try:
                            summary_count += 1
                            logger.info(f"Generating 24-hour summary plot #{summary_count}...")
                            
                            # Load current data
                            td_data = load_time_domain_data(data_logger.time_domain_file)
                            fd_data = load_freq_domain_data(data_logger.freq_domain_file)
                            
                            # Generate summary filename with timestamp
                            current_dt = datetime.utcnow()
                            summary_file = os.path.join(
                                args.output_dir,
                                f'24h_summary_{current_dt.strftime("%Y%m%d_%H%M%S")}.png'
                            )
                            
                            # Create title suffix with time range
                            time_range = f"{start_time.strftime('%Y-%m-%d %H:%M')} to {current_dt.strftime('%Y-%m-%d %H:%M')} UTC"
                            
                            plot_24hour_summary(td_data, fd_data, summary_file, time_range)
                            logger.info(f"24-hour summary saved to: {summary_file}")
                            
                            last_summary_time = current_time
                        except Exception as e:
                            logger.error(f"Error generating 24-hour summary: {e}", exc_info=True)
                
                # Sleep for a short interval
                time.sleep(1.0)
            
            except Exception as e:
                logger.error(f"Error in measurement cycle: {e}", exc_info=True)
                time.sleep(5.0)  # Wait before retry
        
        # Graceful shutdown
        logger.info("Shutting down...")
        
        # Final status display
        display_status(td_analyzer, fd_analyzer, multi_receiver)
        
        # Generate final 24-hour summary if enabled
        if config.LOGGING['generate_24h_summary'] and VISUALIZATION_AVAILABLE:
            try:
                logger.info("Generating final 24-hour summary...")
                
                # Load all data
                td_data = load_time_domain_data(data_logger.time_domain_file)
                fd_data = load_freq_domain_data(data_logger.freq_domain_file)
                
                # Generate final summary
                end_time = datetime.utcnow()
                final_summary_file = os.path.join(
                    args.output_dir,
                    f'24h_summary_final_{data_logger.session_id}.png'
                )
                
                time_range = f"{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC"
                plot_24hour_summary(td_data, fd_data, final_summary_file, time_range)
                logger.info(f"Final 24-hour summary saved to: {final_summary_file}")
            except Exception as e:
                logger.error(f"Error generating final 24-hour summary: {e}", exc_info=True)
        
        # Generate final report
        logger.info("Generating final report...")
        report_file = report_gen.save_report()
        logger.info(f"Final report saved to: {report_file}")
        
        # Update session info with end time
        session_info['end_time'] = datetime.utcnow().isoformat()
        data_logger.save_session_info(session_info)
        
        # Stop receivers
        multi_receiver.shutdown()
        
        logger.info("Shutdown complete")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        multi_receiver.shutdown()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
