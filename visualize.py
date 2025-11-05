#!/usr/bin/env python3
"""
Visualization tools for WWV/WWVH discrimination data.
"""

import argparse
import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import numpy as np


def load_time_domain_data(csv_file):
    """
    Load time-domain data from CSV file.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        Dictionary mapping frequency to list of measurements
    """
    data = {}
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            freq = row['frequency']
            if freq not in data:
                data[freq] = {'wwv': [], 'wwvh': [], 'timestamps': []}
            
            station = row['station']
            timestamp = datetime.fromisoformat(row['timestamp'])
            
            measurement = {
                'timestamp': timestamp,
                'rssi_dbm': float(row['rssi_dbm']),
                'power_db': float(row['power_db']),
                'snr_db': float(row['snr_db']),
                'noise_floor_db': float(row['noise_floor_db']),
            }
            
            data[freq][station].append(measurement)
            if timestamp not in data[freq]['timestamps']:
                data[freq]['timestamps'].append(timestamp)
    
    return data


def load_freq_domain_data(csv_file):
    """
    Load frequency-domain data from CSV file.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        Dictionary mapping frequency to list of measurements
    """
    data = {}
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            freq = row['frequency']
            if freq not in data:
                data[freq] = []
            
            timestamp = datetime.fromisoformat(row['timestamp'])
            
            measurement = {
                'timestamp': timestamp,
                'wwv_power_db': float(row['wwv_power_db']),
                'wwvh_power_db': float(row['wwvh_power_db']),
                'ratio_db': float(row['ratio_db']) if row['ratio_db'] != 'N/A' else None,
            }
            
            data[freq].append(measurement)
    
    return data


def plot_time_domain_analysis(data, output_file='time_domain_plot.png'):
    """
    Plot time-domain analysis results.
    
    Args:
        data: Time-domain data dictionary
        output_file: Output filename
    """
    frequencies = sorted(data.keys())
    num_freqs = len(frequencies)
    
    fig, axes = plt.subplots(num_freqs, 2, figsize=(15, 4*num_freqs))
    if num_freqs == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle('Time-Domain Analysis: Absolute Carrier Strength', fontsize=16, fontweight='bold')
    
    for i, freq in enumerate(frequencies):
        freq_data = data[freq]
        
        # RSSI plot
        ax1 = axes[i, 0]
        
        if freq_data['wwv']:
            wwv_times = [m['timestamp'] for m in freq_data['wwv']]
            wwv_rssi = [m['rssi_dbm'] for m in freq_data['wwv']]
            ax1.plot(wwv_times, wwv_rssi, 'b.-', label='WWV', linewidth=2, markersize=6)
        
        if freq_data['wwvh']:
            wwvh_times = [m['timestamp'] for m in freq_data['wwvh']]
            wwvh_rssi = [m['rssi_dbm'] for m in freq_data['wwvh']]
            ax1.plot(wwvh_times, wwvh_rssi, 'r.-', label='WWVH', linewidth=2, markersize=6)
        
        ax1.set_title(f'{freq} - RSSI')
        ax1.set_ylabel('RSSI (dBm)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # SNR plot
        ax2 = axes[i, 1]
        
        if freq_data['wwv']:
            wwv_times = [m['timestamp'] for m in freq_data['wwv']]
            wwv_snr = [m['snr_db'] for m in freq_data['wwv']]
            ax2.plot(wwv_times, wwv_snr, 'b.-', label='WWV', linewidth=2, markersize=6)
        
        if freq_data['wwvh']:
            wwvh_times = [m['timestamp'] for m in freq_data['wwvh']]
            wwvh_snr = [m['snr_db'] for m in freq_data['wwvh']]
            ax2.plot(wwvh_times, wwvh_snr, 'r.-', label='WWVH', linewidth=2, markersize=6)
        
        ax2.set_title(f'{freq} - SNR')
        ax2.set_ylabel('SNR (dB)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved time-domain plot to {output_file}")


def plot_freq_domain_analysis(data, output_file='freq_domain_plot.png'):
    """
    Plot frequency-domain analysis results.
    
    Args:
        data: Frequency-domain data dictionary
        output_file: Output filename
    """
    frequencies = sorted(data.keys())
    num_freqs = len(frequencies)
    
    fig, axes = plt.subplots(num_freqs, 2, figsize=(15, 4*num_freqs))
    if num_freqs == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle('Frequency-Domain Analysis: Marker Tone Power', fontsize=16, fontweight='bold')
    
    for i, freq in enumerate(frequencies):
        freq_data = data[freq]
        
        times = [m['timestamp'] for m in freq_data]
        wwv_power = [m['wwv_power_db'] for m in freq_data]
        wwvh_power = [m['wwvh_power_db'] for m in freq_data]
        ratios = [m['ratio_db'] for m in freq_data if m['ratio_db'] is not None]
        ratio_times = [m['timestamp'] for m in freq_data if m['ratio_db'] is not None]
        
        # Power plot
        ax1 = axes[i, 0]
        ax1.plot(times, wwv_power, 'b.-', label='WWV (1000 Hz)', linewidth=1, markersize=4)
        ax1.plot(times, wwvh_power, 'r.-', label='WWVH (1200 Hz)', linewidth=1, markersize=4)
        ax1.set_title(f'{freq} - Marker Tone Power')
        ax1.set_ylabel('Power (dB)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Ratio plot
        ax2 = axes[i, 1]
        if ratios:
            ax2.plot(ratio_times, ratios, 'g.-', linewidth=1, markersize=4)
            ax2.axhline(y=0, color='k', linestyle='--', alpha=0.5)
            ax2.fill_between(ratio_times, 0, ratios, 
                            where=[r > 0 for r in ratios],
                            alpha=0.3, color='blue', label='WWV stronger')
            ax2.fill_between(ratio_times, 0, ratios,
                            where=[r < 0 for r in ratios],
                            alpha=0.3, color='red', label='WWVH stronger')
        
        ax2.set_title(f'{freq} - Discrimination Ratio')
        ax2.set_ylabel('WWV - WWVH (dB)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved frequency-domain plot to {output_file}")


def plot_discrimination_comparison(td_data, fd_data, output_file='discrimination_comparison.png'):
    """
    Compare discrimination ratios from both methods.
    
    Args:
        td_data: Time-domain data dictionary
        fd_data: Frequency-domain data dictionary
        output_file: Output filename
    """
    frequencies = sorted(set(list(td_data.keys()) + list(fd_data.keys())))
    
    fig, axes = plt.subplots(len(frequencies), 1, figsize=(12, 4*len(frequencies)))
    if len(frequencies) == 1:
        axes = [axes]
    
    fig.suptitle('Discrimination Ratio Comparison: Time-Domain vs Frequency-Domain',
                fontsize=16, fontweight='bold')
    
    for i, freq in enumerate(frequencies):
        ax = axes[i]
        
        # Time-domain ratios
        if freq in td_data:
            wwv_data = td_data[freq]['wwv']
            wwvh_data = td_data[freq]['wwvh']
            
            # Pair up measurements by closest time
            td_ratios = []
            td_times = []
            
            for wwv_m in wwv_data:
                # Find closest WWVH measurement
                closest_wwvh = min(wwvh_data, 
                                 key=lambda m: abs((m['timestamp'] - wwv_m['timestamp']).total_seconds()),
                                 default=None)
                
                if closest_wwvh and abs((closest_wwvh['timestamp'] - wwv_m['timestamp']).total_seconds()) < 300:
                    ratio = wwv_m['rssi_dbm'] - closest_wwvh['rssi_dbm']
                    td_ratios.append(ratio)
                    td_times.append(wwv_m['timestamp'])
            
            if td_ratios:
                ax.plot(td_times, td_ratios, 'bs-', label='Time-Domain (hourly)',
                       linewidth=2, markersize=8, alpha=0.7)
        
        # Frequency-domain ratios
        if freq in fd_data:
            fd_times = [m['timestamp'] for m in fd_data[freq] if m['ratio_db'] is not None]
            fd_ratios = [m['ratio_db'] for m in fd_data[freq] if m['ratio_db'] is not None]
            
            if fd_ratios:
                ax.plot(fd_times, fd_ratios, 'r.-', label='Frequency-Domain (per-minute)',
                       linewidth=1, markersize=3, alpha=0.5)
        
        ax.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        ax.set_title(freq)
        ax.set_ylabel('Discrimination Ratio (dB)\n(+) WWV stronger, (-) WWVH stronger')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved comparison plot to {output_file}")


def plot_24hour_summary(td_data, fd_data, output_file='24hour_summary.png', title_suffix=''):
    """
    Create comprehensive 24-hour summary plot.
    
    Args:
        td_data: Time-domain data dictionary
        fd_data: Frequency-domain data dictionary
        output_file: Output filename
        title_suffix: Additional text for title (e.g., date range)
    """
    frequencies = sorted(set(list(td_data.keys()) + list(fd_data.keys())))
    
    # Create figure with custom layout
    fig = plt.figure(figsize=(20, 14))
    gs = GridSpec(5, 4, figure=fig, hspace=0.3, wspace=0.3)
    
    # Main title
    title = f'WWV/WWVH 24-Hour Discrimination Summary'
    if title_suffix:
        title += f' - {title_suffix}'
    fig.suptitle(title, fontsize=18, fontweight='bold')
    
    # Row 0: Time-domain RSSI for all frequencies
    for i, freq in enumerate(frequencies):
        ax = fig.add_subplot(gs[0, i])
        freq_data = td_data.get(freq, {'wwv': [], 'wwvh': []})
        
        if freq_data['wwv']:
            wwv_times = [m['timestamp'] for m in freq_data['wwv']]
            wwv_rssi = [m['rssi_dbm'] for m in freq_data['wwv']]
            ax.plot(wwv_times, wwv_rssi, 'b.-', label='WWV', linewidth=2, markersize=8)
        
        if freq_data['wwvh']:
            wwvh_times = [m['timestamp'] for m in freq_data['wwvh']]
            wwvh_rssi = [m['rssi_dbm'] for m in freq_data['wwvh']]
            ax.plot(wwvh_times, wwvh_rssi, 'r.-', label='WWVH', linewidth=2, markersize=8)
        
        ax.set_title(f'{freq}\nAbsolute RSSI', fontsize=10, fontweight='bold')
        ax.set_ylabel('RSSI (dBm)')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # Row 1: Time-domain SNR for all frequencies
    for i, freq in enumerate(frequencies):
        ax = fig.add_subplot(gs[1, i])
        freq_data = td_data.get(freq, {'wwv': [], 'wwvh': []})
        
        if freq_data['wwv']:
            wwv_times = [m['timestamp'] for m in freq_data['wwv']]
            wwv_snr = [m['snr_db'] for m in freq_data['wwv']]
            ax.plot(wwv_times, wwv_snr, 'b.-', label='WWV', linewidth=2, markersize=8)
        
        if freq_data['wwvh']:
            wwvh_times = [m['timestamp'] for m in freq_data['wwvh']]
            wwvh_snr = [m['snr_db'] for m in freq_data['wwvh']]
            ax.plot(wwvh_times, wwvh_snr, 'r.-', label='WWVH', linewidth=2, markersize=8)
        
        ax.set_title(f'{freq}\nSNR', fontsize=10, fontweight='bold')
        ax.set_ylabel('SNR (dB)')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # Row 2: Frequency-domain marker powers
    for i, freq in enumerate(frequencies):
        ax = fig.add_subplot(gs[2, i])
        freq_data = fd_data.get(freq, [])
        
        if freq_data:
            times = [m['timestamp'] for m in freq_data]
            wwv_power = [m['wwv_power_db'] for m in freq_data]
            wwvh_power = [m['wwvh_power_db'] for m in freq_data]
            
            ax.plot(times, wwv_power, 'b-', label='WWV (1000 Hz)', linewidth=1, alpha=0.7)
            ax.plot(times, wwvh_power, 'r-', label='WWVH (1200 Hz)', linewidth=1, alpha=0.7)
        
        ax.set_title(f'{freq}\nMarker Tone Power', fontsize=10, fontweight='bold')
        ax.set_ylabel('Power (dB)')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # Row 3: Discrimination ratios (frequency-domain)
    for i, freq in enumerate(frequencies):
        ax = fig.add_subplot(gs[3, i])
        freq_data = fd_data.get(freq, [])
        
        if freq_data:
            times = [m['timestamp'] for m in freq_data if m['ratio_db'] is not None]
            ratios = [m['ratio_db'] for m in freq_data if m['ratio_db'] is not None]
            
            if ratios:
                ax.plot(times, ratios, 'g-', linewidth=1.5)
                ax.axhline(y=0, color='k', linestyle='--', alpha=0.5)
                ax.fill_between(times, 0, ratios,
                               where=[r > 0 for r in ratios],
                               alpha=0.3, color='blue', label='WWV stronger')
                ax.fill_between(times, 0, ratios,
                               where=[r < 0 for r in ratios],
                               alpha=0.3, color='red', label='WWVH stronger')
        
        ax.set_title(f'{freq}\nDiscrimination Ratio', fontsize=10, fontweight='bold')
        ax.set_ylabel('WWV - WWVH (dB)')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # Row 4: Summary statistics panel
    ax_stats = fig.add_subplot(gs[4, :])
    ax_stats.axis('off')
    
    # Compute summary statistics
    stats_text = ['24-HOUR SUMMARY STATISTICS\n']
    stats_text.append('=' * 100 + '\n\n')
    
    for freq in frequencies:
        stats_text.append(f'{freq}:\n')
        
        # Time-domain stats
        td_freq = td_data.get(freq, {'wwv': [], 'wwvh': []})
        if td_freq['wwv']:
            wwv_rssi = [m['rssi_dbm'] for m in td_freq['wwv']]
            stats_text.append(f'  WWV (Time-Domain):  Count={len(wwv_rssi):2d}  '
                            f'Mean RSSI={np.mean(wwv_rssi):+6.1f} dBm  '
                            f'Std={np.std(wwv_rssi):5.1f} dB  '
                            f'Range=[{np.min(wwv_rssi):+.1f}, {np.max(wwv_rssi):+.1f}]\n')
        
        if td_freq['wwvh']:
            wwvh_rssi = [m['rssi_dbm'] for m in td_freq['wwvh']]
            stats_text.append(f'  WWVH (Time-Domain): Count={len(wwvh_rssi):2d}  '
                            f'Mean RSSI={np.mean(wwvh_rssi):+6.1f} dBm  '
                            f'Std={np.std(wwvh_rssi):5.1f} dB  '
                            f'Range=[{np.min(wwvh_rssi):+.1f}, {np.max(wwvh_rssi):+.1f}]\n')
        
        # Freq-domain stats
        fd_freq = fd_data.get(freq, [])
        if fd_freq:
            ratios = [m['ratio_db'] for m in fd_freq if m['ratio_db'] is not None]
            if ratios:
                mean_ratio = np.mean(ratios)
                dominant = 'WWV' if mean_ratio > 0 else 'WWVH'
                stats_text.append(f'  Freq-Domain:        Count={len(ratios):2d}  '
                                f'Mean Ratio={mean_ratio:+6.1f} dB  '
                                f'Std={np.std(ratios):5.1f} dB  '
                                f'Dominant: {dominant}\n')
        
        stats_text.append('\n')
    
    # Add overall assessment
    stats_text.append('OVERALL ASSESSMENT:\n')
    all_ratios = {}
    for freq in frequencies:
        fd_freq = fd_data.get(freq, [])
        ratios = [m['ratio_db'] for m in fd_freq if m['ratio_db'] is not None]
        if ratios:
            all_ratios[freq] = np.mean(ratios)
    
    if all_ratios:
        overall_mean = np.mean(list(all_ratios.values()))
        if overall_mean > 2:
            assessment = 'WWV DOMINANT - Propagation favors Fort Collins path'
        elif overall_mean < -2:
            assessment = 'WWVH DOMINANT - Propagation favors Kauai path'
        else:
            assessment = 'BALANCED - Both stations roughly equal strength'
        stats_text.append(f'  {assessment}\n')
        stats_text.append(f'  Mean discrimination across all bands: {overall_mean:+.1f} dB\n')
    
    ax_stats.text(0.05, 0.95, ''.join(stats_text),
                 transform=ax_stats.transAxes,
                 fontsize=9,
                 verticalalignment='top',
                 fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved 24-hour summary to {output_file}")
    plt.close(fig)


def main():
    """Main visualization entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize WWV/WWVH discrimination data'
    )
    
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Directory containing CSV data files'
    )
    
    parser.add_argument(
        '--session',
        help='Session ID (timestamp) to visualize. If not specified, uses most recent.'
    )
    
    parser.add_argument(
        '--output-dir',
        default='plots',
        help='Directory for output plots'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find data files
    if args.session:
        td_file = os.path.join(args.data_dir, f'time_domain_{args.session}.csv')
        fd_file = os.path.join(args.data_dir, f'freq_domain_{args.session}.csv')
    else:
        # Find most recent files
        td_files = [f for f in os.listdir(args.data_dir) if f.startswith('time_domain_')]
        fd_files = [f for f in os.listdir(args.data_dir) if f.startswith('freq_domain_')]
        
        if not td_files or not fd_files:
            print("No data files found!")
            return 1
        
        td_file = os.path.join(args.data_dir, sorted(td_files)[-1])
        fd_file = os.path.join(args.data_dir, sorted(fd_files)[-1])
    
    print(f"Loading data from:")
    print(f"  Time-domain: {td_file}")
    print(f"  Frequency-domain: {fd_file}")
    
    # Load data
    td_data = load_time_domain_data(td_file)
    fd_data = load_freq_domain_data(fd_file)
    
    # Generate plots
    print("\nGenerating plots...")
    
    plot_time_domain_analysis(
        td_data,
        os.path.join(args.output_dir, 'time_domain.png')
    )
    
    plot_freq_domain_analysis(
        fd_data,
        os.path.join(args.output_dir, 'freq_domain.png')
    )
    
    plot_discrimination_comparison(
        td_data,
        fd_data,
        os.path.join(args.output_dir, 'comparison.png')
    )
    
    # Generate 24-hour summary
    plot_24hour_summary(
        td_data,
        fd_data,
        os.path.join(args.output_dir, '24hour_summary.png')
    )
    
    print("\nVisualization complete!")


if __name__ == '__main__':
    import sys
    sys.exit(main())
