# WWV/WWVH Discrimination Application - Architecture

## Overview

This application implements a dual-approach system for discriminating between WWV (Fort Collins, CO) and WWVH (Kauai, HI) time signal broadcasts on multiple HF frequencies. It leverages the ka9q-radio system for SDR signal reception and processing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ka9q-radio (radiod)                     │
│                   SDR Hardware Interface                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ RTP Streams (16 kHz IQ, 16-bit)
                 │ - 2.5 MHz
                 │ - 5 MHz
                 │ - 10 MHz  
                 │ - 15 MHz
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│            stream_receiver.py                                │
│         MultiFrequencyReceiver                               │
│  - RTP packet reception and parsing                          │
│  - IQ sample buffering (circular buffers)                    │
│  - Multi-frequency stream management                         │
└────────────┬────────────────────────────────────────────────┘
             │
             │ IQ Sample Buffers
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────────┐  ┌──────────────┐
│time_domain.py│  │freq_domain.py│
│             │  │              │
│ Approach 1  │  │  Approach 2  │
└──────┬──────┘  └──────┬───────┘
       │                │
       │ Measurements   │
       │                │
       ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    data_logger.py                            │
│                   DataLogger & ReportGenerator               │
│  - CSV logging (time-domain, freq-domain, statistics)       │
│  - Session tracking                                          │
│  - Report generation                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Data Files
                          ▼
                   ┌─────────────┐
                   │  data/      │
                   │  *.csv      │
                   │  *.json     │
                   └─────────────┘
                          │
                          │
                          ▼
                   ┌─────────────┐
                   │visualize.py │
                   │ Matplotlib  │
                   └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  plots/     │
                   │  *.png      │
                   └─────────────┘
```

## Module Descriptions

### Core Modules

#### `config.py`
Central configuration for all parameters:
- Frequency definitions (2.5, 5, 10, 15 MHz)
- Sample rate (16 kHz IQ)
- Time-domain parameters (measurement windows)
- Frequency-domain parameters (tone frequencies, DSP settings)
- Data logging configuration
- Radiod connection settings

#### `signal_processing.py`
DSP utilities library:
- Power calculations (dB, dBm, RSSI)
- Noise floor estimation
- SNR computation
- Bandpass filtering
- Goertzel algorithm for single-frequency detection
- Tone detection with configurable thresholds
- Spectrum analysis (FFT)
- AM demodulation for audio extraction

#### `stream_receiver.py`

**Classes:**
- `RTPReceiver`: Single-frequency RTP stream handler
  - RTP packet parsing
  - IQ sample extraction and scaling
  - Circular buffer management (configurable duration)
  - Packet loss detection
  - Statistics tracking
  
- `MultiFrequencyReceiver`: Multi-frequency coordinator
  - Manages 4 RTPReceiver instances (one per frequency)
  - Radiod connection and channel creation
  - Multicast group configuration
  - Aggregate statistics

**Key Features:**
- Threaded reception for non-blocking operation
- Proper RTP header parsing (version, sequence, SSRC)
- Automatic sample rate conversion (int16 → float32 → complex64)
- Buffer overflow protection

### Analysis Modules

#### `time_domain.py` - Approach 1: Absolute Carrier Strength

**Classes:**
- `TimeDomainAnalyzer`: Single-frequency time-domain analysis
  - Minute 1 detection (WWVH 440 Hz tone, WWV silent)
  - Minute 2 detection (WWV 440 Hz tone, WWVH silent)
  - Carrier strength measurement (RSSI, power, SNR)
  - Tone verification
  - Measurement storage and statistics
  
- `MultiFrequencyTimeDomainAnalyzer`: Multi-frequency coordinator
  - Parallel analysis across all frequencies
  - Aggregate statistics
  - Discrimination ratio computation

**Measurement Windows:**
- WWVH: Minute 1, seconds 15-59 (44 seconds)
- WWV: Minute 2, seconds 15-59 (44 seconds)

**Output Metrics:**
- RSSI (dBm) - absolute carrier strength
- Power (dB) - relative power
- Noise floor (dB)
- SNR (dB)
- Tone presence verification

#### `freq_domain.py` - Approach 2: Simultaneous Marker Analysis

**Classes:**
- `FrequencyDomainAnalyzer`: Single-frequency marker analysis
  - Every-minute marker detection (except minutes 29, 59)
  - WWV 1000 Hz marker power
  - WWVH 1200 Hz marker power
  - Simultaneous measurement (800 ms window)
  - Ratio computation
  - Temporal variation analysis
  
- `MultiFrequencyFreqDomainAnalyzer`: Multi-frequency coordinator
  - Parallel analysis across all frequencies
  - Propagation characteristic analysis
  - Frequency-dependent discrimination patterns

**Measurement Approach:**
- Bandpass filtering around 1000 Hz and 1200 Hz
- Goertzel algorithm for precise single-frequency measurement
- Power ratio computation (WWV/WWVH)
- Detection threshold: -40 dB (configurable)

**Output Metrics:**
- WWV marker power (dB)
- WWVH marker power (dB)
- Detection flags (above/below threshold)
- Ratio (dB): positive = WWV stronger, negative = WWVH stronger

### Data Management

#### `data_logger.py`

**Classes:**
- `DataLogger`: Data persistence manager
  - Session-based file naming
  - CSV format with headers
  - Three output streams:
    1. Time-domain measurements
    2. Frequency-domain measurements
    3. Statistical summaries
  - JSON session metadata
  
- `ReportGenerator`: Summary report creation
  - Text-based summary reports
  - Statistics aggregation
  - Per-frequency summaries

**CSV Formats:**

Time-Domain CSV:
```
timestamp,frequency,station,minute,second,rssi_dbm,power_db,noise_floor_db,snr_db,tone_present,tone_power_db,num_samples,duration
```

Frequency-Domain CSV:
```
timestamp,frequency,minute,second,wwv_detected,wwv_power_db,wwv_goertzel_db,wwvh_detected,wwvh_power_db,wwvh_goertzel_db,ratio_db,num_samples,duration
```

### Application Entry Points

#### `main.py`
Primary application:
- Command-line argument parsing
- Graceful shutdown handling (SIGINT)
- Continuous measurement loop
- Status display (periodic)
- Integrated logging of both approaches
- Final report generation

**Operation:**
1. Connect to radiod
2. Create channels for all frequencies
3. Start RTP receivers
4. Initialize both analyzers
5. Run measurement loop:
   - Check time-domain windows
   - Check frequency-domain windows
   - Log measurements
   - Display status periodically
6. Generate final report on shutdown

#### `visualize.py`
Post-processing visualization:
- Load CSV data files
- Generate matplotlib plots:
  1. Time-domain: RSSI and SNR over time
  2. Frequency-domain: Marker power over time
  3. Comparison: Both methods side-by-side
- Configurable plot styling
- Multi-frequency subplots

#### `example_usage.py`
Educational examples demonstrating:
- Basic receiver setup
- Time-domain analysis only
- Frequency-domain analysis only
- Full integrated system
- Interactive menu selection

## Data Flow

### Time-Domain Path (Hourly)

```
RTP Stream → RTPReceiver Buffer → Check UTC time
                                      ↓
                          Is it minute 1 or 2?
                                      ↓
                          Extract 10s of samples
                                      ↓
                          Compute RSSI, SNR, etc.
                                      ↓
                          Verify 440 Hz tone
                                      ↓
                          Log measurement
                                      ↓
                          Update statistics
```

### Frequency-Domain Path (Per-Minute)

```
RTP Stream → RTPReceiver Buffer → Check UTC time
                                      ↓
                         Is it top of minute?
                          (except 29, 59)
                                      ↓
                          Extract 0.8s window
                                      ↓
                          Demodulate to audio
                                      ↓
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            Filter @ 1000 Hz                    Filter @ 1200 Hz
            (WWV marker)                        (WWVH marker)
                    │                                   │
                    ▼                                   ▼
            Compute power                       Compute power
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                            Compute ratio (dB)
                                      ↓
                            Log measurement
                                      ↓
                            Update statistics
```

## DSP Pipeline Details

### IQ Sample Processing

1. **RTP Reception**: 16-bit signed integers (I, Q interleaved)
2. **Normalization**: Scale to [-1.0, +1.0] float32
3. **Complex Formation**: I + jQ (complex64)
4. **Buffering**: Circular buffer (120 seconds typical)

### Audio Extraction (for marker detection)

1. **AM Demodulation**: |IQ| = sqrt(I² + Q²)
2. **DC Removal**: subtract mean
3. **Normalization**: scale to [-1.0, +1.0]

### Tone Detection

1. **Bandpass Filter**: Butterworth 4th-order, ±25 Hz bandwidth
2. **Power Computation**: Mean of squared magnitudes
3. **Threshold Comparison**: -40 dB default
4. **Goertzel Verification**: Single-bin DFT for precision

### Spectrum Analysis

1. **Windowing**: Hann window (configurable)
2. **FFT**: Configurable size (2048 default)
3. **Power Spectrum**: |FFT|² in dB scale

## Performance Considerations

### Memory Usage

- Circular buffers: 120s × 16kHz × 8 bytes = 15.4 MB per frequency
- Total for 4 frequencies: ~62 MB
- Plus processing overhead: ~100 MB total typical

### CPU Usage

- RTP reception: Minimal (4 threads, mostly blocked on I/O)
- DSP processing: Moderate
  - Time-domain: Runs every ~60 seconds
  - Freq-domain: Runs every 60 seconds
- Typical load: <10% on modern CPU

### Network Usage

- Sample rate: 16 kHz complex (32k samples/s real)
- Bits per sample: 16 (I) + 16 (Q) = 32 bits
- Bandwidth per stream: 16000 × 4 bytes = 64 kB/s = 512 kbps
- Total for 4 frequencies: 256 kB/s = 2 Mbps

### Disk Usage

- CSV logging: ~1 KB per measurement
- Time-domain: 2 measurements/hour/frequency = 8/hour
- Freq-domain: ~58 measurements/hour/frequency = 232/hour
- Total: ~240 KB/hour typical

## Extensibility

### Adding Frequencies

1. Edit `config.py`: Add to `FREQUENCIES` dictionary
2. No code changes needed (automatic scaling)

### Custom Analysis

Extend base analyzer classes:
- Override `run_measurement_cycle()`
- Add custom DSP in `signal_processing.py`
- Create new CSV output in `data_logger.py`

### Different Presets

Change `config.PRESET`:
- `"iq"`: Complex IQ (current, most flexible)
- `"am"`: AM demodulated audio
- `"usb"`, `"lsb"`: SSB demodulated
- `"fm"`: FM demodulated

### Integration

All modules are importable:
```python
from stream_receiver import MultiFrequencyReceiver
from time_domain import TimeDomainAnalyzer
# ... use programmatically
```

## Dependencies

### Required
- `ka9q` - ka9q-radio Python interface
- `numpy` - Numerical arrays and math
- `scipy` - DSP filters and functions
- `matplotlib` - Visualization (visualize.py only)

### System
- `ka9q-radio` - SDR receiver system (external)
- Python 3.8+ with threading support
- Multicast-capable network

## Error Handling

- Graceful degradation: Missing data → skip measurement
- Packet loss tracking and logging
- Connection retry logic (configurable)
- Exception logging with traceback
- Clean shutdown on SIGINT

## Testing

Use `example_usage.py` for incremental testing:
1. Basic connectivity (option 1)
2. Individual analysis methods (options 2-3)
3. Full integration (option 4)

## Future Enhancements

Potential additions:
- Real-time web dashboard
- Kalman filtering for smoothing
- Machine learning for propagation prediction
- Automatic report generation and emailing
- Integration with propagation databases
- Multi-day statistical analysis
- Antenna array processing (direction finding)
