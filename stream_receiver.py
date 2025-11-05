"""
RTP stream receiver for WWV/WWVH monitoring.
Manages multiple frequency streams using ka9q-radio.
"""

import socket
import struct
import threading
import logging
from collections import deque
from datetime import datetime
import numpy as np
from ka9q import RadiodControl
import config


logger = logging.getLogger(__name__)


class RTPReceiver:
    """
    Receives and buffers RTP streams for a single frequency.
    """
    
    def __init__(self, ssrc, multicast_group, port, buffer_seconds=60):
        """
        Initialize RTP receiver.
        
        Args:
            ssrc: Stream SSRC identifier
            multicast_group: Multicast IP address
            port: UDP port
            buffer_seconds: Size of circular buffer in seconds
        """
        self.ssrc = ssrc
        self.multicast_group = multicast_group
        self.port = port
        self.buffer_seconds = buffer_seconds
        
        # Calculate buffer size in samples
        self.buffer_size = config.SAMPLE_RATE * buffer_seconds
        self.sample_buffer = deque(maxlen=self.buffer_size)
        
        # Threading
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Socket
        self.sock = None
        
        # Statistics
        self.packets_received = 0
        self.samples_received = 0
        self.last_sequence = None
        self.packet_loss_count = 0
        
    def start(self):
        """Start receiving RTP packets."""
        if self.running:
            logger.warning(f"RTP receiver for SSRC {self.ssrc} already running")
            return
        
        # Create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to port
        self.sock.bind(('', self.port))
        
        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Start receiver thread
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Started RTP receiver for SSRC {self.ssrc} on {self.multicast_group}:{self.port}")
    
    def stop(self):
        """Stop receiving RTP packets."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.sock:
            self.sock.close()
            self.sock = None
        
        logger.info(f"Stopped RTP receiver for SSRC {self.ssrc}")
    
    def _receive_loop(self):
        """Main receiver loop."""
        self.sock.settimeout(1.0)  # 1 second timeout for clean shutdown
        packet_count = 0
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65536)
                packet_count += 1
                if packet_count == 1:
                    logger.info(f"SSRC {self.ssrc}: First packet received!")
                self._process_packet(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving RTP packet: {e}")
    
    def _process_packet(self, data):
        """
        Process incoming RTP packet.
        
        RTP Header Format (12 bytes minimum):
        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |V=2|P|X|  CC   |M|     PT      |       sequence number         |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                           timestamp                           |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |           synchronization source (SSRC) identifier            |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        if len(data) < 12:
            return
        
        # Parse RTP header
        header = struct.unpack('!BBHII', data[:12])
        version = (header[0] >> 6) & 0x03
        padding = (header[0] >> 5) & 0x01
        extension = (header[0] >> 4) & 0x01
        cc = header[0] & 0x0F
        marker = (header[1] >> 7) & 0x01
        payload_type = header[1] & 0x7F
        sequence = header[2]
        timestamp = header[3]
        ssrc = header[4]
        
        # Verify SSRC matches
        if ssrc != self.ssrc:
            return
        
        # Check for packet loss
        if self.last_sequence is not None:
            expected_seq = (self.last_sequence + 1) & 0xFFFF
            if sequence != expected_seq:
                loss = (sequence - expected_seq) & 0xFFFF
                self.packet_loss_count += loss
                logger.warning(f"Packet loss detected: expected {expected_seq}, got {sequence} (loss: {loss})")
        
        self.last_sequence = sequence
        
        # Calculate payload offset
        header_size = 12 + (cc * 4)
        if extension:
            if len(data) < header_size + 4:
                return
            ext_header = struct.unpack('!HH', data[header_size:header_size+4])
            ext_length = ext_header[1] * 4
            header_size += 4 + ext_length
        
        # Extract payload (IQ samples as 16-bit signed integers)
        payload = data[header_size:]
        
        # Remove padding if present
        if padding and len(payload) > 0:
            padding_length = payload[-1]
            payload = payload[:-padding_length]
        
        # Convert to complex IQ samples
        # Assuming interleaved I/Q format: I1, Q1, I2, Q2, ...
        if len(payload) % 4 != 0:
            logger.warning(f"Payload size {len(payload)} not multiple of 4")
            return
        
        num_samples = len(payload) // 4
        samples = np.frombuffer(payload, dtype=np.int16).astype(np.float32)
        
        # Scale to [-1, 1] range
        samples = samples / 32768.0
        
        # Create complex samples
        i_samples = samples[0::2]
        q_samples = samples[1::2]
        iq_samples = i_samples + 1j * q_samples
        
        # Add to buffer
        with self.lock:
            self.sample_buffer.extend(iq_samples)
            self.samples_received += len(iq_samples)
            self.packets_received += 1
    
    def get_samples(self, duration_seconds=None, clear=False):
        """
        Retrieve samples from buffer.
        
        Args:
            duration_seconds: Duration of samples to retrieve (None = all)
            clear: Clear retrieved samples from buffer
            
        Returns:
            NumPy array of complex IQ samples
        """
        with self.lock:
            if duration_seconds is None:
                num_samples = len(self.sample_buffer)
            else:
                num_samples = int(duration_seconds * config.SAMPLE_RATE)
                num_samples = min(num_samples, len(self.sample_buffer))
            
            if num_samples == 0:
                return np.array([], dtype=np.complex64)
            
            # Get samples from end of buffer (most recent)
            samples = np.array(list(self.sample_buffer)[-num_samples:], dtype=np.complex64)
            
            if clear:
                for _ in range(num_samples):
                    self.sample_buffer.pop()
            
            return samples
    
    def get_statistics(self):
        """Get receiver statistics."""
        return {
            'ssrc': self.ssrc,
            'packets_received': self.packets_received,
            'samples_received': self.samples_received,
            'packet_loss_count': self.packet_loss_count,
            'buffer_fill': len(self.sample_buffer) / self.buffer_size,
        }


class MultiFrequencyReceiver:
    """
    Manages RTP receivers for multiple frequencies.
    """
    
    def __init__(self, radiod_host=None):
        """
        Initialize multi-frequency receiver.
        
        Args:
            radiod_host: Hostname or IP of radiod server
        """
        self.radiod_host = radiod_host or config.RADIOD['default_host']
        self.control = None
        self.receivers = {}
        self.channels_created = False
        self.channel_map = {}  # Maps freq_name -> (ssrc, channel_info)
        
    def connect(self):
        """Connect to radiod and create channels."""
        logger.info(f"Connecting to radiod at {self.radiod_host}")
        
        try:
            self.control = RadiodControl(self.radiod_host)
            logger.info("Connected to radiod")
        except Exception as e:
            logger.error(f"Failed to connect to radiod: {e}")
            raise
        
        # Create channels for each frequency
        self._create_channels()
    
    def _create_channels(self):
        """Discover and verify existing channels are available."""
        from ka9q.discovery import discover_channels
        
        logger.info("Discovering existing channels on radiod...")
        logger.info(f"Listening to status multicast from {self.radiod_host}...")
        
        try:
            # Try discovery with longer timeout
            all_channels = discover_channels(self.radiod_host, listen_duration=5.0)
            
            if not all_channels:
                logger.warning(
                    f"Discovery received 0 status packets from {self.radiod_host}. "
                    "This may indicate radiod is not broadcasting status on multicast, "
                    "or a network/firewall issue is blocking multicast reception."
                )
                logger.warning(
                    "Will use expected SSRCs without verification. "
                    "You MUST provide RTP data address via --multicast and --rtp-port!"
                )
                
                # Fallback: use expected SSRCs without verification
                for name, freq in config.FREQUENCIES.items():
                    ssrc = config.get_ssrc(freq)
                    self.channel_map[name] = (ssrc, None)
                    logger.info(f"Using expected channel: {name}, SSRC={ssrc}")
            else:
                # Discovery succeeded
                logger.info(f"✓ Discovered {len(all_channels)} existing channels")
                
                # Map our frequencies to discovered channels
                for name, freq in config.FREQUENCIES.items():
                    ssrc = config.get_ssrc(freq)  # SSRCs are frequency in Hz
                    
                    if ssrc in all_channels:
                        # Found the channel
                        channel_info = all_channels[ssrc]
                        self.channel_map[name] = (ssrc, channel_info)
                        logger.info(
                            f"✓ Found channel for {name}: "
                            f"SSRC={ssrc}, {channel_info.frequency/1e6:.3f} MHz, "
                            f"{channel_info.preset}, {channel_info.sample_rate} Hz"
                        )
                    else:
                        # Channel not in discovery results - assume it exists
                        logger.warning(
                            f"Channel {name} (SSRC={ssrc}) not in discovery results, "
                            "but will attempt to use it anyway"
                        )
                        self.channel_map[name] = (ssrc, None)
            
            if not self.channel_map:
                raise RuntimeError(
                    "No channels configured. Expected SSRCs: " +
                    ", ".join(str(config.get_ssrc(f)) for f in config.FREQUENCIES.values())
                )
            
            self.channels_created = True
            logger.info(f"Ready to receive from {len(self.channel_map)} channels")
            
        except Exception as e:
            logger.error(f"Failed during channel setup: {e}")
            raise
    
    def start_receivers(self, multicast_group=None, port=None):
        """
        Start RTP receivers for all frequencies.
        
        Args:
            multicast_group: RTP multicast address (if None, will auto-discover)
            port: RTP port (if None, will auto-discover)
        
        All channels use the SAME multicast group and port (configured in radiod).
        They are differentiated by SSRC in the RTP packets.
        """
        if not self.channels_created:
            raise RuntimeError("Channels not created - call connect() first")
        
        # Use provided address or discover from radiod
        if multicast_group and port:
            logger.info(f"Using manual RTP data address: {multicast_group}:{port}")
        else:
            logger.info("Auto-discovering RTP data address from radiod...")
            try:
                multicast_group, port = self._discover_rtp_address()
            except Exception as e:
                logger.error(
                    "Failed to discover RTP data address. "
                    "You must provide it manually using --multicast and --rtp-port"
                )
                raise RuntimeError(
                    "RTP data address discovery failed. "
                    "Restart with: --multicast <addr> --rtp-port <port>"
                ) from e
        
        logger.info(f"All channels will receive RTP on {multicast_group}:{port} (differentiated by SSRC)")
        
        # Create receivers for all frequencies on the SAME port
        for name, (ssrc, channel_info) in self.channel_map.items():
            receiver = RTPReceiver(
                ssrc=ssrc,
                multicast_group=multicast_group,
                port=port,
                buffer_seconds=120  # 2 minutes of buffering
            )
            
            receiver.start()
            self.receivers[name] = receiver
            
            freq = config.FREQUENCIES[name]
            logger.info(f"Started receiver for {name} ({freq/1e6:.1f} MHz), SSRC={ssrc}")
    
    def stop_receivers(self):
        """Stop all RTP receivers."""
        for name, receiver in self.receivers.items():
            receiver.stop()
            logger.info(f"Stopped receiver for {name}")
        
        self.receivers.clear()
    
    def get_receiver(self, freq_name):
        """
        Get receiver for a specific frequency.
        
        Args:
            freq_name: Frequency name (e.g., '10MHz')
            
        Returns:
            RTPReceiver instance
        """
        return self.receivers.get(freq_name)
    
    def _discover_rtp_address(self):
        """
        Discover RTP output address and port from radiod.
        
        Returns:
            tuple: (multicast_address, port)
            
        Raises:
            RuntimeError: If discovery fails or no channels found
        """
        try:
            from ka9q.discovery import discover_channels
            
            logger.info(f"Discovering RTP output address from {self.radiod_host}...")
            channels = discover_channels(self.radiod_host, listen_duration=3.0)
            
            if not channels:
                raise RuntimeError(
                    f"No channels discovered from {self.radiod_host}. "
                    "Ensure radiod is running and has active channels."
                )
            
            # Find output destination from one of our expected WWV channels
            # (since radiod may have multiple multicast groups)
            multicast_addr = None
            port = None
            
            for name, freq in config.FREQUENCIES.items():
                ssrc = config.get_ssrc(freq)
                if ssrc in channels:
                    ch = channels[ssrc]
                    if ch.multicast_address and ch.port:
                        multicast_addr = ch.multicast_address
                        port = ch.port
                        logger.debug(f"Using RTP address from WWV channel {name}: {multicast_addr}:{port}")
                        break
            
            # Fallback: use first channel's destination if no WWV channels found
            if not multicast_addr or not port:
                first_channel = next(iter(channels.values()))
                multicast_addr = first_channel.multicast_address
                port = first_channel.port
                logger.warning(f"No WWV channels found, using first channel's address")
            
            if not multicast_addr or not port:
                raise RuntimeError(
                    f"No channels have RTP output destination. "
                    "Check radiod configuration for 'data' multicast address."
                )
            
            logger.info(f"Discovered RTP output: {multicast_addr}:{port}")
            logger.info(f"Found {len(channels)} existing channels on radiod")
            
            # Log discovered channels for debugging
            for ssrc, ch in channels.items():
                logger.debug(
                    f"  Channel {ssrc}: {ch.frequency/1e6:.3f} MHz, "
                    f"{ch.preset}, {ch.sample_rate} Hz"
                )
            
            return multicast_addr, port
            
        except Exception as e:
            logger.error(f"Failed to discover RTP address from radiod: {e}")
            raise RuntimeError(
                f"Could not discover RTP output from {self.radiod_host}. "
                "Ensure radiod is running and configured with multicast output."
            ) from e
    
    def get_all_statistics(self):
        """Get statistics for all receivers."""
        stats = {}
        for name, receiver in self.receivers.items():
            stats[name] = receiver.get_statistics()
        return stats
    
    def shutdown(self):
        """Shutdown all receivers and close connection."""
        self.stop_receivers()
        logger.info("Multi-frequency receiver shutdown complete")
