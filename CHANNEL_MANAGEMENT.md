# Channel Management & SSRC Assignment

## Overview

The application manages RTP channels on the ka9q-radio system for four HF frequencies. This document explains how channels are created and how SSRC identifiers are assigned.

## SSRC (Synchronization Source) Identifiers

### What is SSRC?

SSRC is a **32-bit unsigned integer** identifier used in RTP (Real-time Transport Protocol) streams, as defined in RFC 3550. 

**Important**: SSRC is **numeric only** - it cannot be alphanumeric.

- **Valid range**: 0 to 4,294,967,295
- **Format**: Unsigned 32-bit integer
- **Purpose**: Uniquely identifies each RTP stream

### SSRC Assignment Strategy

We use **frequency in kHz** as the SSRC value for simplicity and readability:

| Frequency | Frequency (kHz) | SSRC Value |
|-----------|-----------------|------------|
| 2.5 MHz   | 2,500 kHz       | 2500       |
| 5.0 MHz   | 5,000 kHz       | 5000       |
| 10.0 MHz  | 10,000 kHz      | 10000      |
| 15.0 MHz  | 15,000 kHz      | 15000      |

**Previous approach**: Used frequency in Hz (e.g., 2500000), which was valid but less readable.

**Current approach**: Frequency in kHz (e.g., 2500) - cleaner and easier to work with.

### Code Implementation

```python
# In config.py
def get_ssrc(freq_hz):
    """Generate SSRC from frequency in kHz.
    
    Args:
        freq_hz: Frequency in Hz
        
    Returns:
        int: SSRC value (frequency in kHz)
    """
    return int(freq_hz / 1000)
```

Usage:
```python
>>> get_ssrc(2.5e6)
2500
>>> get_ssrc(10.0e6)
10000
```

## Channel Creation Process

### Intelligent Channel Management

The application now **checks if channels already exist** before attempting to create them. This prevents errors when:

1. Channels were created by a previous run
2. Multiple instances try to create the same channels
3. Channels already exist from manual configuration

### Workflow

```
1. Connect to radiod
   ↓
2. For each frequency:
   ↓
   2a. Check if channel exists (verify_channel)
       ↓
       Exists and correct? → Skip to next frequency
       ↓
       Doesn't exist or misconfigured? → Continue
       ↓
   2b. Create channel (create_and_configure_channel)
       ↓
3. All channels verified/created
   ↓
4. Start RTP receivers
```

### Code Implementation

```python
# In stream_receiver.py, _create_channels() method

for name, freq in config.FREQUENCIES.items():
    ssrc = config.get_ssrc(freq)
    
    # First check if channel already exists
    if self.control.verify_channel(ssrc=ssrc, expected_freq=freq):
        logger.info(f"Channel for {name} already exists")
        continue
    
    # Create if it doesn't exist
    self.control.create_and_configure_channel(
        ssrc=ssrc,
        frequency_hz=freq,
        preset=config.PRESET,
        sample_rate=config.SAMPLE_RATE
    )
```

## API Methods Used

### `verify_channel(ssrc, expected_freq=None)`

Checks if a channel exists and is configured correctly.

**Args**:
- `ssrc` (int): SSRC to verify
- `expected_freq` (float, optional): Expected frequency in Hz

**Returns**:
- `True` if channel exists and matches expectations
- `False` otherwise

**Example**:
```python
if control.verify_channel(ssrc=2500, expected_freq=2.5e6):
    print("Channel 2500 (2.5 MHz) exists and is correct")
```

### `create_and_configure_channel(...)`

Creates and configures a new channel.

**Args**:
- `ssrc` (int): SSRC identifier
- `frequency_hz` (float): Frequency in Hz
- `preset` (str): Preset mode (e.g., "iq", "usb", "lsb")
- `sample_rate` (int, optional): Output sample rate
- `gain` (float, optional): Gain in dB
- `agc_enable` (bool, optional): Enable automatic gain control

**Example**:
```python
control.create_and_configure_channel(
    ssrc=2500,
    frequency_hz=2.5e6,
    preset="iq",
    sample_rate=16000
)
```

## Benefits of This Approach

### 1. **Prevents Duplicate Channels**
- Won't try to create channels that already exist
- Safe to restart the application multiple times

### 2. **Cleaner SSRC Values**
- 2500 is easier to work with than 2500000
- Logs are more readable
- Debugging is simpler

### 3. **Robust Error Handling**
- Verifies channels before use
- Clear logging of what's being created vs. reused
- Graceful handling of existing channels

### 4. **Better Logging**

Before:
```
Creating channel for 2.5MHz (2.5 MHz), SSRC=2500000
Channel created for 2.5MHz
```

After:
```
Checking/creating channel for 2.5MHz (2.5 MHz), SSRC=2500
Channel for 2.5MHz already exists and is configured correctly
```

## Troubleshooting

### Channel Already Exists Error

**Problem**: Error when trying to create a channel that already exists.

**Solution**: This is now handled automatically. The application checks first and reuses existing channels.

### SSRC Conflict

**Problem**: Two applications trying to use the same SSRC.

**Current**: Using frequency in kHz (2500, 5000, 10000, 15000) minimizes conflicts.

**Alternative**: If conflicts still occur, modify `config.py` to add an offset:

```python
def get_ssrc(freq_hz):
    # Add offset to avoid conflicts with other apps
    SSRC_OFFSET = 10000
    return int(freq_hz / 1000) + SSRC_OFFSET
```

This would give SSRCs: 12500, 15000, 20000, 25000

### Wrong Frequency

**Problem**: Channel exists but at wrong frequency.

**Solution**: `verify_channel()` checks frequency match and will recreate if different:

```python
if self.control.verify_channel(ssrc=ssrc, expected_freq=freq):
    # Channel exists AND frequency matches
else:
    # Will be created with correct frequency
```

## Migration from Old Code

If you have an older version that used frequency in Hz:

1. **Old SSRCs**: 2500000, 5000000, 10000000, 15000000
2. **New SSRCs**: 2500, 5000, 10000, 15000

The application will:
- Not find the old channels (different SSRC)
- Create new channels with new SSRCs
- Old channels will remain but unused
- You can manually delete old channels if desired

## Manual Channel Management

### List All Channels

```bash
# Using ka9q-radio tools
radiodctl list
```

### Delete a Channel

```bash
# Using ka9q-radio tools
radiodctl delete <ssrc>
```

### Check Channel Status

The application logs channel status on startup:

```
Channel for 2.5MHz already exists and is configured correctly
Channel for 5MHz already exists and is configured correctly
Channel for 10MHz already exists and is configured correctly
Channel for 15MHz already exists and is configured correctly
All channels verified/created successfully
```

## Summary

✅ **SSRC is numeric only** (not alphanumeric)  
✅ **Using frequency in kHz** for clean values (2500, 5000, 10000, 15000)  
✅ **Check before create** to prevent errors  
✅ **Reuse existing channels** when possible  
✅ **Better logging** for troubleshooting  
✅ **Robust and reliable** channel management
