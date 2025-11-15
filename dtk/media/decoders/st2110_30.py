"""ST 2110-30 Audio decoder for uncompressed PCM audio streams."""

import struct
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from ..rtp_extractor import RTPPacketInfo, RTPStreamInfo


@dataclass
class AudioStreamParams:
    """Parameters for an ST 2110-30 audio stream."""
    sample_rate: int  # Hz (typically 48000 or 96000)
    bit_depth: int  # bits per sample (16, 20, or 24)
    channels: int  # number of audio channels
    encoding: str = "L"  # L for linear PCM (big-endian)

    @property
    def bytes_per_sample(self) -> int:
        """Calculate bytes per sample."""
        return self.bit_depth // 8

    @property
    def frame_size(self) -> int:
        """Calculate frame size in bytes (all channels)."""
        return self.channels * self.bytes_per_sample


class ST211030Decoder:
    """Decoder for ST 2110-30 uncompressed PCM audio streams."""

    # Common sample rates for professional audio
    COMMON_SAMPLE_RATES = [48000, 96000, 44100, 88200]

    # Supported bit depths
    SUPPORTED_BIT_DEPTHS = [16, 20, 24]

    def __init__(self, params: Optional[AudioStreamParams] = None):
        """Initialize audio decoder.

        Args:
            params: Audio stream parameters. If None, will auto-detect.
        """
        self.params = params
        self.samples: Optional[np.ndarray] = None

    def decode(self, packets: List[RTPPacketInfo], stream_info: RTPStreamInfo) -> np.ndarray:
        """Decode RTP packets to audio samples.

        Args:
            packets: List of RTP packets containing audio data
            stream_info: Information about the RTP stream

        Returns:
            Numpy array of audio samples (channels, samples)
        """
        if self.params is None:
            self.params = self._detect_params(packets, stream_info)

        # Concatenate all payload data
        payload_data = b''.join(pkt.payload for pkt in packets)

        # Decode based on bit depth
        samples = self._decode_samples(payload_data)

        self.samples = samples
        return samples

    def _detect_params(self, packets: List[RTPPacketInfo],
                       stream_info: RTPStreamInfo) -> AudioStreamParams:
        """Auto-detect audio stream parameters.

        Args:
            packets: List of RTP packets
            stream_info: Stream information

        Returns:
            Detected audio parameters
        """
        # Get total payload size
        total_payload = sum(len(pkt.payload) for pkt in packets)

        # Estimate duration from RTP timestamps
        # RTP timestamp units are based on sample rate
        timestamp_diff = stream_info.last_timestamp - stream_info.first_timestamp

        # Try common sample rates to find best match
        best_params = None
        best_error = float('inf')

        for sample_rate in self.COMMON_SAMPLE_RATES:
            for bit_depth in self.SUPPORTED_BIT_DEPTHS:
                for channels in [1, 2, 4, 8, 16]:  # Common channel counts
                    bytes_per_sample = bit_depth // 8
                    frame_size = channels * bytes_per_sample

                    # Calculate expected number of samples
                    if timestamp_diff > 0:
                        expected_samples = timestamp_diff
                        expected_bytes = expected_samples * channels * bytes_per_sample

                        error = abs(expected_bytes - total_payload)

                        if error < best_error:
                            best_error = error
                            best_params = AudioStreamParams(
                                sample_rate=sample_rate,
                                bit_depth=bit_depth,
                                channels=channels
                            )

        if best_params is None or best_error > total_payload * 0.1:  # 10% error margin
            # Fallback to common defaults
            # Assume 48kHz, 24-bit, stereo
            best_params = AudioStreamParams(
                sample_rate=48000,
                bit_depth=24,
                channels=2
            )

        return best_params

    def _decode_samples(self, payload_data: bytes) -> np.ndarray:
        """Decode payload bytes to audio samples.

        Args:
            payload_data: Raw payload bytes

        Returns:
            Numpy array of samples (channels, samples)
        """
        if self.params is None:
            raise ValueError("Audio parameters not set")

        bytes_per_sample = self.params.bytes_per_sample
        channels = self.params.channels
        frame_size = self.params.frame_size

        # Calculate number of complete frames
        num_frames = len(payload_data) // frame_size
        valid_data = payload_data[:num_frames * frame_size]

        if self.params.bit_depth == 16:
            # 16-bit: standard big-endian signed integers
            samples = np.frombuffer(valid_data, dtype='>i2')
            samples = samples.reshape(-1, channels).T
            # Normalize to float32 [-1.0, 1.0]
            samples = samples.astype(np.float32) / 32768.0

        elif self.params.bit_depth == 24:
            # 24-bit: 3 bytes per sample, big-endian
            samples = self._decode_24bit(valid_data, channels)

        elif self.params.bit_depth == 20:
            # 20-bit: typically packed in 3 bytes, big-endian
            samples = self._decode_20bit(valid_data, channels)

        else:
            raise ValueError(f"Unsupported bit depth: {self.params.bit_depth}")

        return samples

    def _decode_24bit(self, data: bytes, channels: int) -> np.ndarray:
        """Decode 24-bit audio samples.

        Args:
            data: Raw bytes
            channels: Number of channels

        Returns:
            Numpy array (channels, samples) normalized to [-1.0, 1.0]
        """
        # 24-bit samples are 3 bytes each
        num_samples = len(data) // 3
        samples = np.zeros(num_samples, dtype=np.float32)

        for i in range(num_samples):
            # Read 3 bytes in big-endian order
            b1, b2, b3 = data[i*3:(i+1)*3]
            # Combine into 24-bit signed integer
            value = (b1 << 16) | (b2 << 8) | b3
            # Handle sign extension for negative values
            if value & 0x800000:  # Check sign bit
                value -= 0x1000000
            samples[i] = value / 8388608.0  # Normalize to [-1.0, 1.0]

        # Reshape to (channels, samples)
        samples = samples.reshape(-1, channels).T
        return samples

    def _decode_20bit(self, data: bytes, channels: int) -> np.ndarray:
        """Decode 20-bit audio samples.

        Args:
            data: Raw bytes
            channels: Number of channels

        Returns:
            Numpy array (channels, samples) normalized to [-1.0, 1.0]
        """
        # 20-bit samples are typically packed in 3 bytes with 4 bits padding
        num_samples = len(data) // 3
        samples = np.zeros(num_samples, dtype=np.float32)

        for i in range(num_samples):
            # Read 3 bytes in big-endian order
            b1, b2, b3 = data[i*3:(i+1)*3]
            # Combine into 20-bit signed integer (4 LSBs of b3 are padding)
            value = (b1 << 12) | (b2 << 4) | (b3 >> 4)
            # Handle sign extension for negative values
            if value & 0x80000:  # Check sign bit
                value -= 0x100000
            samples[i] = value / 524288.0  # Normalize to [-1.0, 1.0]

        # Reshape to (channels, samples)
        samples = samples.reshape(-1, channels).T
        return samples

    def get_audio_info(self) -> dict:
        """Get information about decoded audio.

        Returns:
            Dictionary with audio information
        """
        if self.params is None or self.samples is None:
            return {}

        num_samples = self.samples.shape[1] if len(self.samples.shape) > 1 else len(self.samples)
        duration = num_samples / self.params.sample_rate

        return {
            'sample_rate': self.params.sample_rate,
            'bit_depth': self.params.bit_depth,
            'channels': self.params.channels,
            'num_samples': num_samples,
            'duration_seconds': duration,
            'duration_formatted': self._format_duration(duration)
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (HH:MM:SS.mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
