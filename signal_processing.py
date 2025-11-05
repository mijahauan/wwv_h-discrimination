"""
Core signal processing utilities for WWV/WWVH discrimination.
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
import config


def compute_power_db(samples):
    """
    Compute power in dB from complex IQ samples.
    
    Args:
        samples: Complex IQ samples
        
    Returns:
        Power in dB
    """
    if len(samples) == 0:
        return -np.inf
    
    power_linear = np.mean(np.abs(samples) ** 2)
    if power_linear <= 0:
        return -np.inf
    
    return 10 * np.log10(power_linear)


def compute_rssi(samples, sample_rate=config.SAMPLE_RATE):
    """
    Compute RSSI (Received Signal Strength Indicator) in dBm.
    
    Args:
        samples: Complex IQ samples
        sample_rate: Sample rate in Hz
        
    Returns:
        RSSI in dBm
    """
    # Calculate RMS power
    rms_power = np.sqrt(np.mean(np.abs(samples) ** 2))
    
    if rms_power <= 0:
        return -np.inf
    
    # Convert to dBm (assuming 50 ohm impedance and proper scaling)
    # This is a relative measurement - absolute calibration would require
    # hardware-specific factors
    dbm = 20 * np.log10(rms_power) + 30  # +30 for mW to dBm
    
    return dbm


def estimate_noise_floor(samples, percentile=10):
    """
    Estimate noise floor from samples.
    
    Args:
        samples: Complex IQ samples
        percentile: Percentile to use for noise floor estimation
        
    Returns:
        Noise floor in dB
    """
    power_samples = np.abs(samples) ** 2
    noise_floor_linear = np.percentile(power_samples, percentile)
    
    if noise_floor_linear <= 0:
        return -np.inf
    
    return 10 * np.log10(noise_floor_linear)


def compute_snr(samples):
    """
    Compute Signal-to-Noise Ratio.
    
    Args:
        samples: Complex IQ samples
        
    Returns:
        SNR in dB
    """
    signal_power = compute_power_db(samples)
    noise_floor = estimate_noise_floor(samples)
    
    return signal_power - noise_floor


def bandpass_filter(samples, center_freq, bandwidth, sample_rate=config.SAMPLE_RATE):
    """
    Apply bandpass filter to samples.
    
    Args:
        samples: Complex IQ samples
        center_freq: Center frequency in Hz
        bandwidth: Filter bandwidth in Hz
        sample_rate: Sample rate in Hz
        
    Returns:
        Filtered samples
    """
    nyquist = sample_rate / 2
    low = (center_freq - bandwidth / 2) / nyquist
    high = (center_freq + bandwidth / 2) / nyquist
    
    # Ensure valid frequency range
    low = max(0.0, min(low, 0.99))
    high = max(0.01, min(high, 1.0))
    
    if low >= high:
        return np.zeros_like(samples)
    
    # Design bandpass filter
    sos = signal.butter(4, [low, high], btype='band', output='sos')
    
    # Apply filter
    filtered = signal.sosfilt(sos, samples)
    
    return filtered


def goertzel_filter(samples, target_freq, sample_rate=config.SAMPLE_RATE):
    """
    Efficient single-frequency detection using Goertzel algorithm.
    
    Args:
        samples: Input samples (real or complex)
        target_freq: Target frequency in Hz
        sample_rate: Sample rate in Hz
        
    Returns:
        Power at target frequency
    """
    N = len(samples)
    if N == 0:
        return 0.0
    
    # If complex, convert to real by taking magnitude
    if np.iscomplexobj(samples):
        samples = np.abs(samples)
    
    # Goertzel algorithm
    k = int(0.5 + (N * target_freq) / sample_rate)
    omega = (2.0 * np.pi * k) / N
    coeff = 2.0 * np.cos(omega)
    
    s_prev = 0.0
    s_prev2 = 0.0
    
    for sample in samples:
        s = sample + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
    
    power = s_prev2**2 + s_prev**2 - coeff * s_prev * s_prev2
    
    return power


def detect_tone(samples, freq, bandwidth=50, sample_rate=config.SAMPLE_RATE, 
                threshold_db=-40):
    """
    Detect presence and power of a specific tone.
    
    Args:
        samples: Complex IQ samples
        freq: Target frequency in Hz
        bandwidth: Detection bandwidth in Hz
        sample_rate: Sample rate in Hz
        threshold_db: Detection threshold in dB
        
    Returns:
        Tuple of (detected: bool, power_db: float)
    """
    # Filter around target frequency
    filtered = bandpass_filter(samples, freq, bandwidth, sample_rate)
    
    # Compute power
    power_db = compute_power_db(filtered)
    
    # Check against threshold
    detected = power_db > threshold_db
    
    return detected, power_db


def compute_spectrum(samples, sample_rate=config.SAMPLE_RATE, 
                     window='hann', nfft=None):
    """
    Compute power spectrum of samples.
    
    Args:
        samples: Complex IQ samples
        sample_rate: Sample rate in Hz
        window: Window function to apply
        nfft: FFT size (default: length of samples)
        
    Returns:
        Tuple of (frequencies, power_spectrum_db)
    """
    if nfft is None:
        nfft = len(samples)
    
    # Apply window
    if window:
        window_func = signal.get_window(window, len(samples))
        samples_windowed = samples * window_func
    else:
        samples_windowed = samples
    
    # Compute FFT
    spectrum = fft(samples_windowed, n=nfft)
    freqs = fftfreq(nfft, 1/sample_rate)
    
    # Compute power spectrum in dB
    power_spectrum = np.abs(spectrum) ** 2
    power_spectrum_db = 10 * np.log10(power_spectrum + 1e-12)  # Add small value to avoid log(0)
    
    return freqs, power_spectrum_db


def extract_audio(iq_samples, sample_rate=config.SAMPLE_RATE):
    """
    Extract audio from IQ samples using AM demodulation.
    
    Args:
        iq_samples: Complex IQ samples
        sample_rate: Sample rate in Hz
        
    Returns:
        Real audio samples
    """
    # AM demodulation: take magnitude of complex signal
    audio = np.abs(iq_samples)
    
    # Remove DC component
    audio = audio - np.mean(audio)
    
    # Normalize
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))
    
    return audio


def moving_average(data, window_size):
    """
    Compute moving average of data.
    
    Args:
        data: Input data array
        window_size: Size of averaging window
        
    Returns:
        Moving average
    """
    if len(data) < window_size:
        return np.mean(data) if len(data) > 0 else 0
    
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')


def detect_marker_onset_times(audio, wwv_freq=1000, wwvh_freq=1200, 
                               bandwidth=50, sample_rate=config.SAMPLE_RATE):
    """
    Detect onset times of WWV and WWVH marker tones.
    
    Uses envelope detection on filtered signals to find when each marker
    starts. This allows calculation of time-of-arrival difference between
    the two stations.
    
    Args:
        audio: Audio signal samples
        wwv_freq: WWV marker frequency (Hz)
        wwvh_freq: WWVH marker frequency (Hz)
        bandwidth: Filter bandwidth (Hz)
        sample_rate: Sample rate (Hz)
        
    Returns:
        Tuple of (wwv_onset_ms, wwvh_onset_ms, time_delta_ms)
        Returns None for onsets if not detected
    """
    if len(audio) == 0:
        return None, None, None
    
    # Filter for each marker tone
    wwv_filtered = bandpass_filter(audio, wwv_freq, bandwidth, sample_rate)
    wwvh_filtered = bandpass_filter(audio, wwvh_freq, bandwidth, sample_rate)
    
    # Compute envelopes (magnitude)
    wwv_envelope = np.abs(wwv_filtered)
    wwvh_envelope = np.abs(wwvh_filtered)
    
    # Smooth envelopes to reduce noise
    window_ms = 10  # 10 ms smoothing window
    window_samples = int(window_ms * sample_rate / 1000)
    if window_samples > 1:
        wwv_envelope = np.convolve(wwv_envelope, 
                                   np.ones(window_samples)/window_samples, 
                                   mode='same')
        wwvh_envelope = np.convolve(wwvh_envelope,
                                    np.ones(window_samples)/window_samples,
                                    mode='same')
    
    # Detect onset as first point exceeding threshold
    # Use 20% of max amplitude as threshold
    wwv_threshold = 0.2 * np.max(wwv_envelope)
    wwvh_threshold = 0.2 * np.max(wwvh_envelope)
    
    # Find first crossing
    wwv_onset_idx = None
    wwvh_onset_idx = None
    
    for i in range(len(wwv_envelope)):
        if wwv_onset_idx is None and wwv_envelope[i] > wwv_threshold:
            wwv_onset_idx = i
        if wwvh_onset_idx is None and wwvh_envelope[i] > wwvh_threshold:
            wwvh_onset_idx = i
        if wwv_onset_idx is not None and wwvh_onset_idx is not None:
            break
    
    # Convert to milliseconds
    wwv_onset_ms = (wwv_onset_idx / sample_rate * 1000) if wwv_onset_idx is not None else None
    wwvh_onset_ms = (wwvh_onset_idx / sample_rate * 1000) if wwvh_onset_idx is not None else None
    
    # Compute time delta (WWV - WWVH)
    # Positive means WWV arrived first, negative means WWVH arrived first
    if wwv_onset_ms is not None and wwvh_onset_ms is not None:
        time_delta_ms = wwv_onset_ms - wwvh_onset_ms
    else:
        time_delta_ms = None
    
    return wwv_onset_ms, wwvh_onset_ms, time_delta_ms
