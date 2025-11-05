"""
Configuration parameters for WWV/WWVH discrimination application.
"""

# Monitored frequencies (Hz)
FREQUENCIES = {
    '2.5MHz': 2.5e6,
    '5MHz': 5.0e6,
    '10MHz': 10.0e6,
    '15MHz': 15.0e6,
}

# RTP stream configuration
SAMPLE_RATE = 16000  # 16 KHz IQ sample rate
PRESET = "iq"  # IQ mode for complex samples
BITS_PER_SAMPLE = 16

# SSRC generation: use frequency in Hz to match existing radiod channels
# Note: SSRC must be a 32-bit unsigned integer (0 to 4,294,967,295)
# Existing channels use: 2500000, 5000000, 10000000, 15000000
def get_ssrc(freq_hz):
    """Generate SSRC from frequency in Hz.
    
    Args:
        freq_hz: Frequency in Hz
        
    Returns:
        int: SSRC value (frequency in Hz)
    """
    return int(freq_hz)

# Time-domain gating parameters (Approach 1)
TIME_DOMAIN = {
    # Minute 1: WWVH transmits 440 Hz, WWV silent
    'wwvh_minute': 1,
    'wwvh_start_second': 15,  # Start at :01:15
    'wwvh_end_second': 59,    # End at :01:59
    'wwvh_tone_freq': 440,    # Hz
    
    # Minute 2: WWV transmits 440 Hz, WWVH silent
    'wwv_minute': 2,
    'wwv_start_second': 15,   # Start at :02:15
    'wwv_end_second': 59,     # End at :02:59
    'wwv_tone_freq': 440,     # Hz
    
    # Measurement parameters
    'measurement_interval': 1.0,  # Seconds between measurements
    'averaging_window': 10.0,     # Seconds to average measurements
}

# Frequency-domain filtering parameters (Approach 2)
FREQ_DOMAIN = {
    # Marker tones at top of each minute (except 29 and 59)
    'wwv_marker_freq': 1000,    # Hz
    'wwvh_marker_freq': 1200,   # Hz
    'marker_duration': 0.8,     # Seconds (800 ms)
    'marker_start_second': 0,   # Top of minute
    
    # DSP parameters
    'filter_bandwidth': 50,      # Hz, bandwidth of bandpass filters
    'goertzel_n': 512,          # Samples for Goertzel algorithm
    'detection_threshold': -40,  # dB, minimum power for detection
    
    # Skip minutes 29 and 59 (no minute markers on these)
    'skip_minutes': [29, 59],
}

# Data logging
LOGGING = {
    'output_dir': 'data',
    'log_format': 'csv',
    'log_interval': 60,  # Seconds between log entries
    'include_raw_iq': False,  # Set to True to save raw IQ samples
    'generate_24h_summary': True,  # Generate 24-hour summary PNG (requires matplotlib)
    'summary_interval_hours': 24,  # Hours between summary generation
}

# Signal processing
SIGNAL_PROCESSING = {
    'fft_size': 2048,
    'window_type': 'hann',
    'overlap': 0.5,  # 50% overlap for STFT
    'noise_floor_percentile': 10,  # Percentile for noise floor estimation
}

# Radiod connection
RADIOD = {
    'default_host': 'radiod.local',
    'connection_timeout': 10.0,  # Seconds
    'retry_interval': 5.0,       # Seconds
    'max_retries': 3,
}
