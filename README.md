# WWV/WWVH Discrimination Application

A Python application for discriminating between WWV (Fort Collins, CO) and WWVH (Kauai, HI) time station broadcasts on multiple HF frequencies using advanced DSP techniques.

## Overview

This application implements two complementary approaches to measure and discriminate WWV and WWVH signals:

1. **Time-Domain Gating (Approach 1)**: Measures absolute RF carrier strength during specific minutes when each station transmits unique tones
   - Minute 1: WWVH transmits 440 Hz tone, WWV silent (measure WWVH)
   - Minute 2: WWV transmits 440 Hz tone, WWVH silent (measure WWV)

2. **Frequency-Domain Filtering (Approach 2)**: Uses DSP to simultaneously measure both stations every minute
   - WWV: 1000 Hz marker tone
   - WWVH: 1200 Hz marker tone
   - Provides high temporal resolution (1 measurement/minute)

## Monitored Frequencies

- 2.5 MHz
- 5.0 MHz
- 10.0 MHz
- 15.0 MHz

## Requirements

- ka9q-radio system with radiod configured
- Python 3.8+
- See `requirements.txt` for Python dependencies

## Installation

### Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

See [QUICKSTART.md](QUICKSTART.md) for detailed installation instructions including ka9q-python setup.

## Usage

### Basic Usage

```bash
python main.py --radiod radiod.local
```

### Advanced Options

```bash
python main.py --radiod radiod.local --output-dir data --log-level DEBUG
```

## Configuration

Edit `config.py` to adjust:
- Monitoring frequencies
- Sample rates
- DSP parameters (filter widths, detection thresholds)
- Time windows for analysis

## Output

The application logs data in CSV format with timestamps, including:
- Absolute carrier strength measurements (dBm) for each station
- Simultaneous relative power measurements
- SNR and signal quality metrics
- Per-frequency discrimination data

### Automatic 24-Hour Summary

The application automatically generates a comprehensive summary PNG every 24 hours (configurable) containing:
- RSSI and SNR time-series plots for all frequencies
- Marker tone power measurements
- Discrimination ratios over time
- Summary statistics and assessment

Summary plots are saved as `24h_summary_YYYYMMDD_HHMMSS.png` in the output directory. A final summary is also generated when the application shuts down.

## Architecture

- `main.py`: Main application entry point
- `stream_receiver.py`: RTP stream management and IQ data reception
- `time_domain.py`: Time-domain gating implementation
- `freq_domain.py`: Frequency-domain filtering implementation
- `signal_processing.py`: Core DSP utilities
- `data_logger.py`: Data logging and storage
- `visualize.py`: Plotting and 24-hour summary generation
- `config.py`: Configuration parameters

## Features

- **Intelligent Channel Management**: Automatically checks if channels exist before creating them
- **Clean SSRC Assignment**: Uses frequency in kHz (2500, 5000, 10000, 15000) for readable identifiers
- **Automatic 24-Hour Summaries**: Generates comprehensive PNG plots every 24 hours
- **Dual Analysis**: Both time-domain (absolute measurements) and frequency-domain (simultaneous discrimination)
- **Robust Logging**: CSV data files with timestamps for all measurements

## References

WWV/WWVH broadcast formats:
- [NIST WWV Information](https://www.nist.gov/pml/time-and-frequency-division/time-distribution/radio-station-wwv)
- [NIST WWVH Information](https://www.nist.gov/pml/time-and-frequency-division/time-distribution/radio-station-wwvh)
