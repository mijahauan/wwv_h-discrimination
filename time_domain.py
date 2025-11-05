"""
Time-domain gating implementation (Approach 1).
Measures absolute carrier strength during unique transmission windows.
"""

import logging
from datetime import datetime, timedelta
import numpy as np
import signal_processing as sp
import config


logger = logging.getLogger(__name__)


class TimeDomainAnalyzer:
    """
    Analyzes WWV/WWVH signals using time-domain gating.
    
    During minute 1: WWVH transmits 440 Hz, WWV silent
    During minute 2: WWV transmits 440 Hz, WWVH silent
    """
    
    def __init__(self, receiver):
        """
        Initialize time-domain analyzer.
        
        Args:
            receiver: RTPReceiver instance
        """
        self.receiver = receiver
        self.measurements = {
            'wwv': [],
            'wwvh': [],
            'timestamps': []
        }
    
    def should_measure_wwvh(self, current_time=None):
        """
        Check if we should measure WWVH (minute 1).
        
        Args:
            current_time: datetime object (default: now)
            
        Returns:
            Tuple of (should_measure: bool, seconds_into_window: int)
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        minute = current_time.minute
        second = current_time.second
        
        if minute == config.TIME_DOMAIN['wwvh_minute']:
            if (config.TIME_DOMAIN['wwvh_start_second'] <= second <= 
                config.TIME_DOMAIN['wwvh_end_second']):
                return True, second - config.TIME_DOMAIN['wwvh_start_second']
        
        return False, 0
    
    def should_measure_wwv(self, current_time=None):
        """
        Check if we should measure WWV (minute 2).
        
        Args:
            current_time: datetime object (default: now)
            
        Returns:
            Tuple of (should_measure: bool, seconds_into_window: int)
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        minute = current_time.minute
        second = current_time.second
        
        if minute == config.TIME_DOMAIN['wwv_minute']:
            if (config.TIME_DOMAIN['wwv_start_second'] <= second <= 
                config.TIME_DOMAIN['wwv_end_second']):
                return True, second - config.TIME_DOMAIN['wwv_start_second']
        
        return False, 0
    
    def measure_carrier_strength(self, duration=10.0):
        """
        Measure carrier strength from recent samples.
        
        Args:
            duration: Duration of samples to analyze (seconds)
            
        Returns:
            Dictionary with measurement results
        """
        # Get recent samples
        samples = self.receiver.get_samples(duration_seconds=duration)
        
        if len(samples) == 0:
            logger.warning("No samples available for measurement")
            return None
        
        # Compute various metrics
        rssi_dbm = sp.compute_rssi(samples)
        power_db = sp.compute_power_db(samples)
        noise_floor = sp.estimate_noise_floor(samples)
        snr = sp.compute_snr(samples)
        
        # Compute spectrum to verify signal characteristics
        freqs, spectrum = sp.compute_spectrum(samples)
        
        measurement = {
            'rssi_dbm': rssi_dbm,
            'power_db': power_db,
            'noise_floor_db': noise_floor,
            'snr_db': snr,
            'num_samples': len(samples),
            'duration': duration,
            'spectrum_peak_db': np.max(spectrum),
            'spectrum_mean_db': np.mean(spectrum),
        }
        
        return measurement
    
    def verify_tone_presence(self, expected_freq=440, duration=5.0):
        """
        Verify that expected tone is present in the signal.
        
        Args:
            expected_freq: Expected tone frequency (Hz)
            duration: Duration to analyze (seconds)
            
        Returns:
            Tuple of (tone_present: bool, tone_power_db: float)
        """
        samples = self.receiver.get_samples(duration_seconds=duration)
        
        if len(samples) == 0:
            return False, -np.inf
        
        # Extract audio from IQ
        audio = sp.extract_audio(samples)
        
        # Detect tone
        detected, power = sp.detect_tone(
            audio,
            expected_freq,
            bandwidth=config.FREQ_DOMAIN['filter_bandwidth']
        )
        
        return detected, power
    
    def run_measurement_cycle(self):
        """
        Run one measurement cycle, checking for appropriate time windows.
        
        Returns:
            Dictionary with measurement results or None if not in measurement window
        """
        current_time = datetime.utcnow()
        
        # Check if we should measure WWVH
        should_wwvh, seconds_wwvh = self.should_measure_wwvh(current_time)
        if should_wwvh:
            logger.info(f"Measuring WWVH (minute 1, {seconds_wwvh}s into window)")
            
            measurement = self.measure_carrier_strength(
                duration=config.TIME_DOMAIN['averaging_window']
            )
            
            if measurement:
                # Verify 440 Hz tone is present (should be WWVH)
                tone_present, tone_power = self.verify_tone_presence(
                    expected_freq=config.TIME_DOMAIN['wwvh_tone_freq']
                )
                
                measurement['station'] = 'wwvh'
                measurement['tone_present'] = tone_present
                measurement['tone_power_db'] = tone_power
                measurement['timestamp'] = current_time
                measurement['minute'] = current_time.minute
                measurement['second'] = current_time.second
                
                self.measurements['wwvh'].append(measurement)
                self.measurements['timestamps'].append(current_time)
                
                logger.info(f"WWVH measurement: RSSI={measurement['rssi_dbm']:.1f} dBm, "
                          f"SNR={measurement['snr_db']:.1f} dB, "
                          f"Tone={'present' if tone_present else 'absent'}")
                
                return measurement
        
        # Check if we should measure WWV
        should_wwv, seconds_wwv = self.should_measure_wwv(current_time)
        if should_wwv:
            logger.info(f"Measuring WWV (minute 2, {seconds_wwv}s into window)")
            
            measurement = self.measure_carrier_strength(
                duration=config.TIME_DOMAIN['averaging_window']
            )
            
            if measurement:
                # Verify 440 Hz tone is present (should be WWV)
                tone_present, tone_power = self.verify_tone_presence(
                    expected_freq=config.TIME_DOMAIN['wwv_tone_freq']
                )
                
                measurement['station'] = 'wwv'
                measurement['tone_present'] = tone_present
                measurement['tone_power_db'] = tone_power
                measurement['timestamp'] = current_time
                measurement['minute'] = current_time.minute
                measurement['second'] = current_time.second
                
                self.measurements['wwv'].append(measurement)
                self.measurements['timestamps'].append(current_time)
                
                logger.info(f"WWV measurement: RSSI={measurement['rssi_dbm']:.1f} dBm, "
                          f"SNR={measurement['snr_db']:.1f} dB, "
                          f"Tone={'present' if tone_present else 'absent'}")
                
                return measurement
        
        return None
    
    def get_latest_measurements(self, count=10):
        """
        Get latest measurements for both stations.
        
        Args:
            count: Number of recent measurements to return
            
        Returns:
            Dictionary with latest WWV and WWVH measurements
        """
        return {
            'wwv': self.measurements['wwv'][-count:] if self.measurements['wwv'] else [],
            'wwvh': self.measurements['wwvh'][-count:] if self.measurements['wwvh'] else [],
        }
    
    def get_statistics(self):
        """
        Get summary statistics for all measurements.
        
        Returns:
            Dictionary with statistical summary
        """
        stats = {}
        
        for station in ['wwv', 'wwvh']:
            measurements = self.measurements[station]
            
            if not measurements:
                stats[station] = {
                    'count': 0,
                    'mean_rssi': None,
                    'std_rssi': None,
                    'mean_snr': None,
                    'std_snr': None,
                }
                continue
            
            rssi_values = [m['rssi_dbm'] for m in measurements]
            snr_values = [m['snr_db'] for m in measurements]
            
            stats[station] = {
                'count': len(measurements),
                'mean_rssi': np.mean(rssi_values),
                'std_rssi': np.std(rssi_values),
                'min_rssi': np.min(rssi_values),
                'max_rssi': np.max(rssi_values),
                'mean_snr': np.mean(snr_values),
                'std_snr': np.std(snr_values),
                'min_snr': np.min(snr_values),
                'max_snr': np.max(snr_values),
            }
        
        return stats
    
    def compute_discrimination_ratio(self):
        """
        Compute the ratio of WWV to WWVH signal strength.
        
        Returns:
            Discrimination ratio in dB (positive = WWV stronger)
        """
        wwv_measurements = self.measurements['wwv']
        wwvh_measurements = self.measurements['wwvh']
        
        if not wwv_measurements or not wwvh_measurements:
            return None
        
        # Use recent measurements
        wwv_rssi = np.mean([m['rssi_dbm'] for m in wwv_measurements[-10:]])
        wwvh_rssi = np.mean([m['rssi_dbm'] for m in wwvh_measurements[-10:]])
        
        # Ratio in dB
        ratio = wwv_rssi - wwvh_rssi
        
        return ratio


class MultiFrequencyTimeDomainAnalyzer:
    """
    Manages time-domain analyzers for multiple frequencies.
    """
    
    def __init__(self, multi_receiver):
        """
        Initialize multi-frequency time-domain analyzer.
        
        Args:
            multi_receiver: MultiFrequencyReceiver instance
        """
        self.multi_receiver = multi_receiver
        self.analyzers = {}
        
        # Create analyzer for each frequency
        for freq_name in config.FREQUENCIES.keys():
            receiver = multi_receiver.get_receiver(freq_name)
            if receiver:
                self.analyzers[freq_name] = TimeDomainAnalyzer(receiver)
    
    def run_measurement_cycle(self):
        """
        Run measurement cycle for all frequencies.
        
        Returns:
            Dictionary mapping frequency name to measurement results
        """
        results = {}
        
        for freq_name, analyzer in self.analyzers.items():
            result = analyzer.run_measurement_cycle()
            if result:
                results[freq_name] = result
        
        return results
    
    def get_all_statistics(self):
        """
        Get statistics for all frequencies.
        
        Returns:
            Dictionary mapping frequency name to statistics
        """
        all_stats = {}
        
        for freq_name, analyzer in self.analyzers.items():
            all_stats[freq_name] = analyzer.get_statistics()
        
        return all_stats
    
    def get_discrimination_ratios(self):
        """
        Get discrimination ratios for all frequencies.
        
        Returns:
            Dictionary mapping frequency name to discrimination ratio
        """
        ratios = {}
        
        for freq_name, analyzer in self.analyzers.items():
            ratio = analyzer.compute_discrimination_ratio()
            if ratio is not None:
                ratios[freq_name] = ratio
        
        return ratios
