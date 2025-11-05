# 24-Hour Summary Feature

## Overview

The application now automatically generates comprehensive 24-hour summary plots at regular intervals and when the application shuts down.

## What's Included

The 24-hour summary PNG contains **5 rows of visualizations** across all monitored frequencies:

### Row 1: Absolute RSSI (Time-Domain)
- Shows WWV and WWVH carrier strength in dBm over time
- Plots data from minute 1 (WWVH) and minute 2 (WWV) measurements
- Provides absolute propagation measurements

### Row 2: SNR (Time-Domain)
- Signal-to-Noise Ratio for both stations
- Shows signal quality over time
- Helps identify poor propagation conditions

### Row 3: Marker Tone Power (Frequency-Domain)
- WWV 1000 Hz marker power
- WWVH 1200 Hz marker power
- Per-minute measurements showing high temporal resolution

### Row 4: Discrimination Ratios
- Real-time WWV vs WWVH discrimination
- Positive values = WWV stronger (blue shading)
- Negative values = WWVH stronger (red shading)
- Shows propagation changes over the 24-hour period

### Row 5: Summary Statistics Panel
- Comprehensive statistics for each frequency
- Mean RSSI, standard deviation, and ranges
- Detection rates for frequency-domain measurements
- **Overall assessment** indicating which station dominates

## Automatic Generation

### During Operation

The application automatically generates a summary plot every 24 hours (configurable):

```python
# In config.py
LOGGING = {
    'generate_24h_summary': True,  # Enable/disable
    'summary_interval_hours': 24,  # Interval
}
```

Files are saved as: `24h_summary_YYYYMMDD_HHMMSS.png`

### On Shutdown

When you stop the application (Ctrl+C), a final summary is automatically generated:

File is saved as: `24h_summary_final_SESSIONID.png`

This captures all data collected during the session, regardless of duration.

## Manual Generation

You can also generate summaries manually at any time:

```bash
python3 visualize.py --data-dir data --output-dir plots
```

This generates `24hour_summary.png` from the latest data files.

## Layout Details

The summary uses a **GridSpec layout** with:
- Figure size: 20" × 14" (optimized for viewing on screen or printing)
- 5 rows × 4 columns (one column per frequency)
- High-resolution output: 150 DPI
- Monospace font for statistics (easier to read aligned data)

## Statistics Interpretation

### Per-Frequency Statistics

For each frequency band, you'll see:

```
2.5MHz:
  WWV (Time-Domain):  Count=12  Mean RSSI= -68.3 dBm  Std=  3.2 dB  Range=[-72.1, -65.4]
  WWVH (Time-Domain): Count=12  Mean RSSI= -75.1 dBm  Std=  4.1 dB  Range=[-80.2, -71.0]
  Freq-Domain:        Count=720 Mean Ratio= +6.8 dB  Std=  2.1 dB  Dominant: WWV
```

**Count**: Number of measurements
- Time-domain: Typically 12-24 per 24 hours (one per hour per station)
- Freq-domain: Typically ~720-1400 per 24 hours (one per minute, skipping minutes 29 and 59)

**Mean RSSI**: Average received signal strength
- More negative = weaker signal
- Typical range: -50 to -90 dBm for WWV/WWVH

**Std**: Standard deviation
- Higher = more variable propagation
- Typical: 2-5 dB for stable paths, 5-15 dB for variable

**Range**: Min and max values observed

**Mean Ratio**: Average discrimination
- Positive = WWV stronger
- Negative = WWVH stronger
- Magnitude indicates how much stronger

### Overall Assessment

At the bottom of the statistics panel:

```
OVERALL ASSESSMENT:
  WWV DOMINANT - Propagation favors Fort Collins path
  Mean discrimination across all bands: +5.2 dB
```

**Thresholds**:
- `> +2 dB`: WWV DOMINANT
- `-2 to +2 dB`: BALANCED
- `< -2 dB`: WWVH DOMINANT

## Use Cases

### Propagation Research
- Track daily propagation patterns
- Compare different frequency bands
- Identify solar activity effects

### Path Analysis
- Determine which propagation path is dominant
- See how paths change throughout the day
- Correlate with solar indices

### Antenna Testing
- Evaluate antenna performance over time
- Compare different antennas (run multiple sessions)
- Verify proper operation

### Education
- Learn about HF propagation
- Visualize ionospheric effects
- Understand frequency-dependent propagation

## Technical Notes

### Memory Usage
The summary generation loads all CSV data into memory:
- Typical 24-hour dataset: 5-10 MB
- Peak memory during plot generation: ~50-100 MB
- Memory is released after plot is saved

### Generation Time
- Small datasets (<1000 points): < 5 seconds
- Typical 24-hour data: 5-15 seconds
- Large datasets (>10000 points): 15-30 seconds

### Error Handling
- If matplotlib is not installed, 24-hour summaries are skipped (warning logged)
- If data files are empty, only available data is plotted
- Missing frequencies are handled gracefully

## Configuration Options

All settings in `config.py`:

```python
LOGGING = {
    'output_dir': 'data',                  # Where to save plots
    'generate_24h_summary': True,          # Enable/disable feature
    'summary_interval_hours': 24,          # Interval between auto-generation
}
```

**To change interval** (e.g., generate every 12 hours):
```python
'summary_interval_hours': 12,
```

**To disable** (only generate on shutdown):
```python
'generate_24h_summary': False,
```

## Example Timeline

For a 48-hour run with default settings:

```
00:00 - Application starts
24:00 - First 24h summary generated: 24h_summary_20241105_000000.png
48:00 - Second 24h summary generated: 24h_summary_20241106_000000.png
48:30 - User stops application
48:30 - Final summary generated: 24h_summary_final_20241104_000000.png
```

## Troubleshooting

### Summary not generating?

1. **Check matplotlib is installed**:
   ```bash
   python3 -c "import matplotlib; print('OK')"
   ```

2. **Check config setting**:
   ```python
   # In config.py
   'generate_24h_summary': True,  # Should be True
   ```

3. **Check logs** for errors:
   ```
   grep "24-hour summary" logfile.txt
   ```

### Empty or partial plots?

- **Early in run**: Normal - plots show all available data
- **Missing frequencies**: Check receiver status
- **No time-domain data**: Wait for minute 1 or 2
- **No freq-domain data**: Check minute markers (not at 29 or 59)

## Integration with Other Tools

The summary PNG files can be:
- Emailed automatically (add script)
- Uploaded to web server (add FTP/rsync)
- Included in reports (link from report generator)
- Archived for long-term analysis

Example cron job to email daily summary:

```bash
#!/bin/bash
# Run after 24 hours of operation
LATEST=$(ls -t data/24h_summary_*.png | head -1)
echo "24-hour WWV/WWVH summary attached" | \
  mail -s "WWV/WWVH Daily Report" -a "$LATEST" you@example.com
```

## Future Enhancements

Potential additions:
- Waterfall-style spectrograms
- Solar index overlay (Kp, SFI, A-index)
- Historical comparison (overlay previous days)
- Multi-day trend analysis
- Interactive HTML version with zoom/pan
