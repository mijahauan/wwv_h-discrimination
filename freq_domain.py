"""
Frequency-domain filtering implementation (Approach 2).
Uses DSP to simultaneously measure WWV and WWVH using marker tones.
"""

import logging
from datetime import datetime, timedelta
import numpy as np
import signal_processing as sp
import config


logger = logging.getLogger(__name__)


class FrequencyDomainAnalyzer:
    """
    Analyzes WWV/WWVH signals using frequency-domain filtering.
    
    Every minute (except 29 and 59):
    - WWV transmits 1000 Hz tone for 800 ms
    - WWVH transmits 1200 Hz tone for 800 ms
    
    These can be measured simultaneously.
    """
    
    def __init__(self, receiver):
        """
        Initialize frequency-domain analyzer.
        
        Args:
            receiver: RTPReceiver instance
        """
        self.receiver = receiver
        self.measurements = []
    
    def should_measure(self, current_time=None):
        """
        Check if we should measure marker tones.
        
        Args:
            current_time: datetime object (default: now)
            
        Returns:
            Tuple of (should_measure: bool, seconds_since_minute_start: float)
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        minute = current_time.minute
        second = current_time.second
        microsecond = current_time.microsecond
        
        # Skip minutes 29 and 59 (no markers)
        if minute in config.FREQ_DOMAIN['skip_minutes']:
            return False, 0.0
        
        # Check if we're in the marker window (0 to 0.8 seconds)
        seconds_since_start = second + microsecond / 1e6
        
        if seconds_since_start <= config.FREQ_DOMAIN['marker_duration']:
            return True, seconds_since_start
        
        # Also allow measurement shortly after marker (for analysis of complete tone)
        if seconds_since_start <= config.FREQ_DOMAIN['marker_duration'] + 0.5:
            return True, seconds_since_start
        
        return False, 0.0
    
    def measure_marker_tones(self):
        """
        Measure both WWV and WWVH marker tones simultaneously.
        
        Returns:
            Dictionary with measurement results
        """
        # Get samples covering the marker duration
        duration = config.FREQ_DOMAIN['marker_duration'] + 0.2  # Add buffer
        samples = self.receiver.get_samples(duration_seconds=duration)
        
        logger.debug(f"Got {len(samples)} samples for measurement")
        
        if len(samples) == 0:
            logger.warning("No samples available for marker tone measurement")
            return None
        
        # Extract audio from IQ
        audio = sp.extract_audio(samples)
        
        # Measure WWV marker (1000 Hz)
        wwv_detected, wwv_power = sp.detect_tone(
            audio,
            config.FREQ_DOMAIN['wwv_marker_freq'],
            bandwidth=config.FREQ_DOMAIN['filter_bandwidth'],
            threshold_db=config.FREQ_DOMAIN['detection_threshold']
        )
        
        # Measure WWVH marker (1200 Hz)
        wwvh_detected, wwvh_power = sp.detect_tone(
            audio,
            config.FREQ_DOMAIN['wwvh_marker_freq'],
            bandwidth=config.FREQ_DOMAIN['filter_bandwidth'],
            threshold_db=config.FREQ_DOMAIN['detection_threshold']
        )
        
        # Use Goertzel for more precise measurement
        wwv_goertzel_power = sp.goertzel_filter(
            audio,
            config.FREQ_DOMAIN['wwv_marker_freq']
        )
        wwvh_goertzel_power = sp.goertzel_filter(
            audio,
            config.FREQ_DOMAIN['wwvh_marker_freq']
        )
        
        # Convert Goertzel power to dB
        wwv_goertzel_db = 10 * np.log10(wwv_goertzel_power + 1e-12)
        wwvh_goertzel_db = 10 * np.log10(wwvh_goertzel_power + 1e-12)
        
        # Compute ratio
        if wwvh_power > -np.inf and wwv_power > -np.inf:
            ratio_db = wwv_power - wwvh_power
        else:
            ratio_db = None
        
        # Detect marker onset times for time delta calculation
        wwv_onset_ms, wwvh_onset_ms, time_delta_ms = sp.detect_marker_onset_times(
            audio,
            wwv_freq=config.FREQ_DOMAIN['wwv_marker_freq'],
            wwvh_freq=config.FREQ_DOMAIN['wwvh_marker_freq'],
            bandwidth=config.FREQ_DOMAIN['filter_bandwidth']
        )
        
        measurement = {
            'wwv_detected': wwv_detected,
            'wwv_power_db': wwv_power,
            'wwv_goertzel_db': wwv_goertzel_db,
            'wwv_onset_ms': wwv_onset_ms,
            'wwvh_detected': wwvh_detected,
            'wwvh_power_db': wwvh_power,
            'wwvh_goertzel_db': wwvh_goertzel_db,
            'wwvh_onset_ms': wwvh_onset_ms,
            'time_delta_ms': time_delta_ms,
            'ratio_db': ratio_db,
            'num_samples': len(samples),
            'duration': duration,
        }
        
        return measurement
    
    def run_measurement_cycle(self):
        """
        Run one measurement cycle, checking for appropriate time.
        
        Returns:
            Dictionary with measurement results or None if not in measurement window
        """
        current_time = datetime.utcnow()
        
        should_measure, seconds_since_start = self.should_measure(current_time)
        
        if not should_measure:
            return None
        
        # Only measure at the start of the minute (wait for marker to complete)
        if seconds_since_start > config.FREQ_DOMAIN['marker_duration']:
            logger.debug(f"Measuring marker tones at minute {current_time.minute}")
            
            measurement = self.measure_marker_tones()
            
            if measurement:
                measurement['timestamp'] = current_time
                measurement['minute'] = current_time.minute
                measurement['second'] = current_time.second
                
                self.measurements.append(measurement)
                
                # Build log message
                log_msg = (f"Marker measurement: "
                          f"WWV={measurement['wwv_power_db']:.1f} dB ({'detected' if measurement['wwv_detected'] else 'absent'}), "
                          f"WWVH={measurement['wwvh_power_db']:.1f} dB ({'detected' if measurement['wwvh_detected'] else 'absent'}), ")
                
                if measurement['ratio_db']:
                    log_msg += f"Ratio={measurement['ratio_db']:.1f} dB"
                else:
                    log_msg += "Ratio=N/A"
                
                if measurement['time_delta_ms'] is not None:
                    log_msg += f", ΔT={measurement['time_delta_ms']:.2f} ms"
                
                logger.info(log_msg)
                
                return measurement
        
        return None
    
    def get_latest_measurements(self, count=10):
        """
        Get latest measurements.
        
        Args:
            count: Number of recent measurements to return
            
        Returns:
            List of recent measurements
        """
        return self.measurements[-count:] if self.measurements else []
    
    def get_statistics(self):
        """
        Get summary statistics for all measurements.
        
        Returns:
            Dictionary with statistical summary
        """
        if not self.measurements:
            return {
                'count': 0,
                'wwv_mean_power': None,
                'wwvh_mean_power': None,
                'mean_ratio': None,
            }
        
        wwv_powers = [m['wwv_power_db'] for m in self.measurements 
                     if m['wwv_power_db'] > -np.inf]
        wwvh_powers = [m['wwvh_power_db'] for m in self.measurements 
                      if m['wwvh_power_db'] > -np.inf]
        ratios = [m['ratio_db'] for m in self.measurements 
                 if m['ratio_db'] is not None]
        
        stats = {
            'count': len(self.measurements),
            'wwv_detection_rate': sum(1 for m in self.measurements if m['wwv_detected']) / len(self.measurements),
            'wwvh_detection_rate': sum(1 for m in self.measurements if m['wwvh_detected']) / len(self.measurements),
        }
        
        if wwv_powers:
            stats['wwv_mean_power'] = np.mean(wwv_powers)
            stats['wwv_std_power'] = np.std(wwv_powers)
            stats['wwv_min_power'] = np.min(wwv_powers)
            stats['wwv_max_power'] = np.max(wwv_powers)
        
        if wwvh_powers:
            stats['wwvh_mean_power'] = np.mean(wwvh_powers)
            stats['wwvh_std_power'] = np.std(wwvh_powers)
            stats['wwvh_min_power'] = np.min(wwvh_powers)
            stats['wwvh_max_power'] = np.max(wwvh_powers)
        
        if ratios:
            stats['mean_ratio'] = np.mean(ratios)
            stats['std_ratio'] = np.std(ratios)
            stats['min_ratio'] = np.min(ratios)
            stats['max_ratio'] = np.max(ratios)
        
        return stats
    
    def compute_discrimination_ratio(self, window=10):
        """
        Compute the ratio of WWV to WWVH signal strength.
        
        Args:
            window: Number of recent measurements to average
            
        Returns:
            Discrimination ratio in dB (positive = WWV stronger)
        """
        if not self.measurements:
            return None
        
        recent = self.measurements[-window:]
        ratios = [m['ratio_db'] for m in recent if m['ratio_db'] is not None]
        
        if not ratios:
            return None
        
        return np.mean(ratios)
    
    def analyze_temporal_variation(self, window_minutes=10):
        """
        Analyze how the discrimination ratio varies over time.
        
        Args:
            window_minutes: Time window for analysis
            
        Returns:
            Dictionary with temporal analysis results
        """
        if len(self.measurements) < 2:
            return None
        
        # Filter measurements to window
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(minutes=window_minutes)
        
        recent = [m for m in self.measurements 
                 if m['timestamp'] >= cutoff_time]
        
        if len(recent) < 2:
            return None
        
        ratios = [m['ratio_db'] for m in recent if m['ratio_db'] is not None]
        timestamps = [m['timestamp'] for m in recent if m['ratio_db'] is not None]
        
        if len(ratios) < 2:
            return None
        
        # Compute variation metrics
        analysis = {
            'mean_ratio': np.mean(ratios),
            'std_ratio': np.std(ratios),
            'min_ratio': np.min(ratios),
            'max_ratio': np.max(ratios),
            'range': np.max(ratios) - np.min(ratios),
            'num_measurements': len(ratios),
            'time_span_minutes': (timestamps[-1] - timestamps[0]).total_seconds() / 60,
        }
        
        return analysis


class MultiFrequencyFreqDomainAnalyzer:
    """
    Manages frequency-domain analyzers for multiple frequencies.
    """
    
    def __init__(self, multi_receiver):
        """
        Initialize multi-frequency frequency-domain analyzer.
        
        Args:
            multi_receiver: MultiFrequencyReceiver instance
        """
        self.multi_receiver = multi_receiver
        self.analyzers = {}
        
        # Create analyzer for each frequency
        for freq_name in config.FREQUENCIES.keys():
            receiver = multi_receiver.get_receiver(freq_name)
            if receiver:
                self.analyzers[freq_name] = FrequencyDomainAnalyzer(receiver)
    
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
    
    def analyze_propagation_characteristics(self):
        """
        Analyze propagation characteristics across all frequencies.
        
        Returns:
            Dictionary with propagation analysis
        """
        ratios = self.get_discrimination_ratios()
        
        if not ratios:
            return None
        
        analysis = {
            'ratios_by_frequency': ratios,
            'mean_ratio': np.mean(list(ratios.values())),
            'std_ratio': np.std(list(ratios.values())),
        }
        
        # Determine which station is stronger overall
        if analysis['mean_ratio'] > 0:
            analysis['dominant_station'] = 'WWV'
            analysis['dominance_db'] = analysis['mean_ratio']
        else:
            analysis['dominant_station'] = 'WWVH'
            analysis['dominance_db'] = abs(analysis['mean_ratio'])
        
        # Frequency-dependent analysis
        freq_values = list(config.FREQUENCIES.values())
        ratio_values = [ratios.get(name, None) for name in config.FREQUENCIES.keys()]
        
        # Check if there's a frequency-dependent pattern
        if all(r is not None for r in ratio_values):
            analysis['frequency_dependency'] = {
                'frequencies_mhz': [f/1e6 for f in freq_values],
                'ratios_db': ratio_values,
            }
        
        return analysis
