"""
Data logging and storage for WWV/WWVH discrimination measurements.
"""

import os
import csv
import logging
from datetime import datetime
import json
import config


logger = logging.getLogger(__name__)


class DataLogger:
    """
    Logs measurement data to CSV files.
    """
    
    def __init__(self, output_dir=None):
        """
        Initialize data logger.
        
        Args:
            output_dir: Directory for output files (default: from config)
        """
        self.output_dir = output_dir or config.LOGGING['output_dir']
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate session ID
        self.session_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # CSV files for each measurement type
        self.time_domain_file = os.path.join(
            self.output_dir,
            f'time_domain_{self.session_id}.csv'
        )
        self.freq_domain_file = os.path.join(
            self.output_dir,
            f'freq_domain_{self.session_id}.csv'
        )
        self.statistics_file = os.path.join(
            self.output_dir,
            f'statistics_{self.session_id}.csv'
        )
        
        # Initialize CSV files with headers
        self._init_time_domain_csv()
        self._init_freq_domain_csv()
        self._init_statistics_csv()
        
        logger.info(f"Data logger initialized for session {self.session_id}")
        logger.info(f"Output directory: {self.output_dir}")
    
    def _init_time_domain_csv(self):
        """Initialize time-domain CSV file with headers."""
        headers = [
            'timestamp',
            'frequency',
            'station',
            'minute',
            'second',
            'rssi_dbm',
            'power_db',
            'noise_floor_db',
            'snr_db',
            'tone_present',
            'tone_power_db',
            'num_samples',
            'duration',
        ]
        
        with open(self.time_domain_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        
        logger.info(f"Created time-domain log: {self.time_domain_file}")
    
    def _init_freq_domain_csv(self):
        """Initialize frequency-domain CSV file with headers."""
        headers = [
            'timestamp',
            'frequency',
            'minute',
            'second',
            'wwv_detected',
            'wwv_power_db',
            'wwv_goertzel_db',
            'wwv_onset_ms',
            'wwvh_detected',
            'wwvh_power_db',
            'wwvh_goertzel_db',
            'wwvh_onset_ms',
            'time_delta_ms',
            'ratio_db',
            'num_samples',
            'duration',
        ]
        
        with open(self.freq_domain_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        
        logger.info(f"Created freq-domain log: {self.freq_domain_file}")
    
    def _init_statistics_csv(self):
        """Initialize statistics CSV file with headers."""
        headers = [
            'timestamp',
            'frequency',
            'analysis_type',
            'statistic_name',
            'value',
        ]
        
        with open(self.statistics_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        
        logger.info(f"Created statistics log: {self.statistics_file}")
    
    def log_time_domain_measurement(self, frequency, measurement):
        """
        Log a time-domain measurement.
        
        Args:
            frequency: Frequency name (e.g., '10MHz')
            measurement: Measurement dictionary
        """
        if not measurement:
            return
        
        row = {
            'timestamp': measurement['timestamp'].isoformat(),
            'frequency': frequency,
            'station': measurement['station'],
            'minute': measurement['minute'],
            'second': measurement['second'],
            'rssi_dbm': f"{measurement['rssi_dbm']:.2f}",
            'power_db': f"{measurement['power_db']:.2f}",
            'noise_floor_db': f"{measurement['noise_floor_db']:.2f}",
            'snr_db': f"{measurement['snr_db']:.2f}",
            'tone_present': measurement['tone_present'],
            'tone_power_db': f"{measurement['tone_power_db']:.2f}",
            'num_samples': measurement['num_samples'],
            'duration': f"{measurement['duration']:.2f}",
        }
        
        with open(self.time_domain_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)
    
    def log_freq_domain_measurement(self, frequency, measurement):
        """
        Log a frequency-domain measurement.
        
        Args:
            frequency: Frequency name (e.g., '10MHz')
            measurement: Measurement dictionary
        """
        if not measurement:
            return
        
        row = {
            'timestamp': measurement['timestamp'].isoformat(),
            'frequency': frequency,
            'minute': measurement['minute'],
            'second': measurement['second'],
            'wwv_detected': measurement['wwv_detected'],
            'wwv_power_db': f"{measurement['wwv_power_db']:.2f}",
            'wwv_goertzel_db': f"{measurement['wwv_goertzel_db']:.2f}",
            'wwv_onset_ms': f"{measurement['wwv_onset_ms']:.2f}" if measurement.get('wwv_onset_ms') is not None else 'N/A',
            'wwvh_detected': measurement['wwvh_detected'],
            'wwvh_power_db': f"{measurement['wwvh_power_db']:.2f}",
            'wwvh_goertzel_db': f"{measurement['wwvh_goertzel_db']:.2f}",
            'wwvh_onset_ms': f"{measurement.get('wwvh_onset_ms'):.2f}" if measurement.get('wwvh_onset_ms') is not None else 'N/A',
            'time_delta_ms': f"{measurement.get('time_delta_ms'):.2f}" if measurement.get('time_delta_ms') is not None else 'N/A',
            'ratio_db': f"{measurement['ratio_db']:.2f}" if measurement['ratio_db'] is not None else 'N/A',
            'num_samples': measurement['num_samples'],
            'duration': f"{measurement['duration']:.2f}",
        }
        
        with open(self.freq_domain_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)
    
    def log_statistics(self, frequency, analysis_type, statistics):
        """
        Log statistics summary.
        
        Args:
            frequency: Frequency name
            analysis_type: Type of analysis ('time_domain' or 'freq_domain')
            statistics: Statistics dictionary
        """
        timestamp = datetime.utcnow().isoformat()
        
        rows = []
        for stat_name, value in statistics.items():
            if value is not None and not isinstance(value, dict):
                rows.append({
                    'timestamp': timestamp,
                    'frequency': frequency,
                    'analysis_type': analysis_type,
                    'statistic_name': stat_name,
                    'value': f"{value:.4f}" if isinstance(value, float) else str(value),
                })
        
        if rows:
            with open(self.statistics_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writerows(rows)
    
    def save_session_info(self, info):
        """
        Save session information to JSON file.
        
        Args:
            info: Dictionary with session information
        """
        info_file = os.path.join(self.output_dir, f'session_{self.session_id}.json')
        
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2, default=str)
        
        logger.info(f"Saved session info to {info_file}")


class ReportGenerator:
    """
    Generates summary reports from logged data.
    """
    
    def __init__(self, logger_instance):
        """
        Initialize report generator.
        
        Args:
            logger_instance: DataLogger instance
        """
        self.logger = logger_instance
    
    def generate_summary_report(self):
        """
        Generate a text summary report.
        
        Returns:
            String with summary report
        """
        report = []
        report.append("=" * 80)
        report.append("WWV/WWVH Discrimination Analysis Summary")
        report.append(f"Session: {self.logger.session_id}")
        report.append("=" * 80)
        report.append("")
        
        # Read statistics file
        try:
            with open(self.logger.statistics_file, 'r') as f:
                reader = csv.DictReader(f)
                stats = list(reader)
            
            if stats:
                report.append("Latest Statistics:")
                report.append("-" * 80)
                
                # Group by frequency and analysis type
                frequencies = set(s['frequency'] for s in stats)
                
                for freq in sorted(frequencies):
                    report.append(f"\nFrequency: {freq}")
                    
                    freq_stats = [s for s in stats if s['frequency'] == freq]
                    
                    # Time domain stats
                    td_stats = [s for s in freq_stats if s['analysis_type'] == 'time_domain']
                    if td_stats:
                        report.append("  Time Domain Analysis:")
                        for stat in td_stats[-10:]:  # Last 10 entries
                            report.append(f"    {stat['statistic_name']}: {stat['value']}")
                    
                    # Freq domain stats
                    fd_stats = [s for s in freq_stats if s['analysis_type'] == 'freq_domain']
                    if fd_stats:
                        report.append("  Frequency Domain Analysis:")
                        for stat in fd_stats[-10:]:  # Last 10 entries
                            report.append(f"    {stat['statistic_name']}: {stat['value']}")
        
        except FileNotFoundError:
            report.append("No statistics available yet.")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, filename=None):
        """
        Save summary report to file.
        
        Args:
            filename: Output filename (default: auto-generated)
        """
        if filename is None:
            filename = os.path.join(
                self.logger.output_dir,
                f'report_{self.logger.session_id}.txt'
            )
        
        report = self.generate_summary_report()
        
        with open(filename, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to {filename}")
        
        return filename
