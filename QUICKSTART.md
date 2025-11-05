# WWV/WWVH Discrimination - Quick Start Guide

## Prerequisites

1. **ka9q-radio system** must be running and accessible
2. **Python 3.8+** installed
3. Your radiod must be configured for the HF bands

## Installation

### Quick Install (Automated)

For a quick automated installation:

```bash
# On macOS/Linux
./install.sh

# On Windows
install.bat
```

The script will:
- Create a virtual environment
- Install ka9q-python from source
- Install all dependencies
- Verify the installation

### Manual Install

If you prefer manual installation:

#### 1. Create Virtual Environment

Modern Python versions require using a virtual environment:

```bash
# Navigate to the repository
cd /Users/mjh/Sync/GitHub/wwv_h-discrimination

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 2. Install ka9q-python from Source

```bash
# Clone ka9q-python (if not already done)
git clone https://github.com/mijahauan/ka9q-python.git
cd ka9q-python

# Upgrade packaging and setuptools first
pip install --upgrade packaging setuptools

# Install ka9q-python in editable mode
pip install -e .

# Return to main directory
cd ..
```

### 3. Install Application Dependencies

```bash
# Make sure you're in the venv and main directory
pip install -r requirements.txt
```

**Note**: Always activate the virtual environment before running the application:
```bash
source venv/bin/activate  # Run this in each new terminal session
```

## Quick Test

Run the example script to test your setup:

```bash
python3 example_usage.py
```

Select option 1 to test basic connectivity.

## Running the Full Application

### Basic Usage

Replace `radiod.local` with the hostname or IP address of your radiod server.

```bash
python3 main.py --radiod bee1-hf-status.local
```

This will:
- Connect to radiod at `radiod.local`
- Create RTP streams for 2.5, 5, 10, and 15 MHz
- Start both time-domain and frequency-domain analysis
- Log data to the `data/` directory
- Display status updates every 5 minutes

### Custom Configuration

```bash
python3 main.py \
  --radiod 192.168.1.100 \
  --multicast 239.1.2.3 \
  --base-port 5004 \
  --output-dir my_data \
  --log-level DEBUG \
  --status-interval 60
```

### Command-Line Options

- `--radiod HOST`: Radiod hostname/IP (default: radiod.local)
- `--multicast ADDR`: Multicast group address (default: 239.1.2.3)
- `--base-port PORT`: Base UDP port for RTP (default: 5004)
- `--output-dir DIR`: Output directory for logs (default: data)
- `--log-level LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `--status-interval SEC`: Status display interval in seconds (default: 300)

## Understanding the Output

### Time-Domain Analysis (Approach 1)

Measures **absolute carrier strength** during specific minutes:

- **Minute 1**: WWVH transmits 440 Hz tone, WWV silent → measures WWVH
- **Minute 2**: WWV transmits 440 Hz tone, WWVH silent → measures WWV

You'll see measurements like:
```
WWVH measurement: RSSI=-65.2 dBm, SNR=18.3 dB, Tone=present
WWV measurement: RSSI=-72.1 dBm, SNR=12.7 dB, Tone=present
```

### Frequency-Domain Analysis (Approach 2)

Measures **both stations simultaneously** every minute using marker tones:

- **WWV**: 1000 Hz marker tone
- **WWVH**: 1200 Hz marker tone

You'll see measurements like:
```
Marker measurement: WWV=-45.3 dB (detected), WWVH=-52.1 dB (detected), Ratio=-6.8 dB
```

### Discrimination Ratio

The ratio tells you which station is stronger:

- **Positive ratio** (+5 dB): WWV is 5 dB stronger than WWVH
- **Negative ratio** (-5 dB): WWVH is 5 dB stronger than WWV
- **Near zero** (±1 dB): Both stations roughly equal

## Data Files

The application creates several files in the output directory:

**CSV Data Files:**
- `time_domain_YYYYMMDD_HHMMSS.csv`: Time-domain measurements
- `freq_domain_YYYYMMDD_HHMMSS.csv`: Frequency-domain measurements
- `statistics_YYYYMMDD_HHMMSS.csv`: Summary statistics
- `session_YYYYMMDD_HHMMSS.json`: Session metadata
- `report_YYYYMMDD_HHMMSS.txt`: Text summary report

**Automatic Summary Plots:**
- `24h_summary_YYYYMMDD_HHMMSS.png`: Generated every 24 hours (configurable)
- `24h_summary_final_SESSIONID.png`: Generated when application stops

The 24-hour summary PNG is a comprehensive visualization containing:
- RSSI and SNR time-series for all frequencies
- Marker tone power measurements
- Discrimination ratios over time
- Summary statistics and overall propagation assessment

## Visualizing Results

### Automatic Visualization

The application automatically generates a comprehensive 24-hour summary plot every 24 hours and when you stop the program. No manual visualization needed!

Look for files like:
- `24h_summary_YYYYMMDD_HHMMSS.png` (generated every 24 hours)
- `24h_summary_final_SESSIONID.png` (generated on shutdown)

### Manual Visualization

You can also generate additional plots at any time:

```bash
python3 visualize.py --data-dir data --output-dir plots
```

This creates four plot files:
- `time_domain.png`: RSSI and SNR over time for both stations
- `freq_domain.png`: Marker tone power over time
- `comparison.png`: Side-by-side comparison of both methods
- `24hour_summary.png`: Comprehensive 24-hour summary (same as automatic)

## Interpreting Results

### Strong WWV Signal
- WWV RSSI > WWVH RSSI
- Positive discrimination ratios
- You're likely closer to Fort Collins, CO or propagation favors that path

### Strong WWVH Signal
- WWVH RSSI > WWV RSSI
- Negative discrimination ratios
- You're likely closer to Kauai, HI or propagation favors that path

### Variable Conditions
- Ratios changing over time indicate variable ionospheric propagation
- Different ratios on different frequencies show frequency-dependent propagation
- This is normal for HF propagation!

## Troubleshooting

### No Data Received

Check that:
1. radiod is running: `systemctl status radiod` (on server)
2. Network connectivity to radiod host
3. Multicast routing is working
4. Firewall allows UDP traffic

### Low Signal Strength

- Normal! WWV/WWVH are 10 kW stations but may be weak depending on:
  - Time of day
  - Solar conditions
  - Your distance from stations
  - Antenna characteristics

### Missing Measurements

Time-domain measurements only occur during specific minutes:
- Minute 1: WWVH
- Minute 2: WWV

Be patient - you'll get one measurement per hour per station per frequency.

Frequency-domain measurements occur every minute (except minutes 29 and 59).

## Tips for Best Results

1. **Run for several hours** to capture propagation changes
2. **Note the time of day** - propagation varies significantly
3. **Compare frequencies** - different bands have different characteristics
4. **Check solar conditions** - WWV/WWVH broadcast this info!
5. **Log continuously** - the more data, the better your analysis

## Next Steps

- Modify `config.py` to adjust analysis parameters
- Add more frequencies if your receiver supports them
- Implement additional analysis in the existing framework
- Compare results with known propagation models

## Getting Help

Check the main README.md for more details, or examine the example scripts in `example_usage.py`.
