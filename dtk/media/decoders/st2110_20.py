"""ST 2110-20 Video decoder for uncompressed video streams."""

import struct
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
from ..rtp_extractor import RTPPacketInfo, RTPStreamInfo


@dataclass
class VideoStreamParams:
    """Parameters for an ST 2110-20 video stream."""
    width: int  # Frame width in pixels
    height: int  # Frame height in pixels
    pixel_format: str  # e.g., 'YCbCr-4:2:2', 'YCbCr-4:4:4', 'RGB'
    bit_depth: int  # Bits per component (8, 10, 12, 16)
    frame_rate: float  # Frames per second
    interlaced: bool = False  # True for interlaced, False for progressive
    packing_mode: str = 'general'  # 'general' or 'block'

    @property
    def bytes_per_pixel(self) -> int:
        """Calculate bytes per pixel based on format and bit depth."""
        if self.pixel_format == 'YCbCr-4:2:2':
            # 4:2:2 has 2 bytes of Y, 1 byte of Cb, 1 byte of Cr per 2 pixels
            components_per_pixel = 2  # Average
        elif self.pixel_format == 'YCbCr-4:4:4':
            components_per_pixel = 3  # Y, Cb, Cr
        elif self.pixel_format == 'RGB':
            components_per_pixel = 3  # R, G, B
        else:
            components_per_pixel = 3  # Default

        bytes_per_component = (self.bit_depth + 7) // 8
        return components_per_pixel * bytes_per_component

    @property
    def frame_size_bytes(self) -> int:
        """Calculate expected frame size in bytes."""
        return self.width * self.height * self.bytes_per_pixel


class ST211020Decoder:
    """Decoder for ST 2110-20 uncompressed video streams."""

    # Common video resolutions (width, height)
    COMMON_RESOLUTIONS = [
        (1920, 1080),  # 1080p/1080i
        (1280, 720),   # 720p
        (3840, 2160),  # 4K UHD
        (4096, 2160),  # 4K DCI
        (7680, 4320),  # 8K UHD
    ]

    # Common frame rates
    COMMON_FRAME_RATES = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]

    def __init__(self, params: Optional[VideoStreamParams] = None):
        """Initialize video decoder.

        Args:
            params: Video stream parameters. If None, will auto-detect.
        """
        self.params = params
        self.frames: List[np.ndarray] = []

    def decode(self, packets: List[RTPPacketInfo], stream_info: RTPStreamInfo) -> List[np.ndarray]:
        """Decode RTP packets to video frames.

        Args:
            packets: List of RTP packets containing video data
            stream_info: Information about the RTP stream

        Returns:
            List of numpy arrays, each representing a video frame
        """
        if self.params is None:
            self.params = self._detect_params(packets, stream_info)

        # Group packets into frames based on marker bit
        frames_data = self._group_into_frames(packets)

        # Decode each frame
        self.frames = []
        for frame_packets in frames_data:
            frame_data = b''.join(pkt.payload for pkt in frame_packets)
            frame = self._decode_frame(frame_data)
            if frame is not None:
                self.frames.append(frame)

        return self.frames

    def _detect_params(self, packets: List[RTPPacketInfo],
                       stream_info: RTPStreamInfo) -> VideoStreamParams:
        """Auto-detect video stream parameters.

        Args:
            packets: List of RTP packets
            stream_info: Stream information

        Returns:
            Detected video parameters
        """
        # Get average frame size by looking at marker-delimited groups
        frames_data = self._group_into_frames(packets)

        if not frames_data:
            # Fallback to 1080p defaults
            return VideoStreamParams(
                width=1920,
                height=1080,
                pixel_format='YCbCr-4:2:2',
                bit_depth=10,
                frame_rate=25.0,
                interlaced=False
            )

        # Calculate average frame size
        avg_frame_size = sum(
            sum(len(p.payload) for p in frame) for frame in frames_data
        ) / len(frames_data)

        # Calculate frame rate from timestamps
        if len(frames_data) > 1:
            time_diff = frames_data[-1][-1].arrival_time - frames_data[0][0].arrival_time
            frame_rate = (len(frames_data) - 1) / time_diff if time_diff > 0 else 25.0
            # Round to nearest common frame rate
            frame_rate = min(self.COMMON_FRAME_RATES, key=lambda x: abs(x - frame_rate))
        else:
            frame_rate = 25.0

        # Try to match resolution and bit depth
        best_params = None
        best_error = float('inf')

        for width, height in self.COMMON_RESOLUTIONS:
            for bit_depth in [8, 10, 12]:
                for pixel_format in ['YCbCr-4:2:2', 'YCbCr-4:4:4', 'RGB']:
                    params = VideoStreamParams(
                        width=width,
                        height=height,
                        pixel_format=pixel_format,
                        bit_depth=bit_depth,
                        frame_rate=frame_rate,
                        interlaced=False
                    )

                    error = abs(params.frame_size_bytes - avg_frame_size)
                    if error < best_error:
                        best_error = error
                        best_params = params

        if best_params is None or best_error > avg_frame_size * 0.2:
            # Fallback to common defaults
            best_params = VideoStreamParams(
                width=1920,
                height=1080,
                pixel_format='YCbCr-4:2:2',
                bit_depth=10,
                frame_rate=frame_rate,
                interlaced=False
            )

        return best_params

    def _group_into_frames(self, packets: List[RTPPacketInfo]) -> List[List[RTPPacketInfo]]:
        """Group RTP packets into frames based on marker bit.

        Args:
            packets: List of RTP packets

        Returns:
            List of lists, where each inner list is packets for one frame
        """
        frames = []
        current_frame = []

        for pkt in packets:
            current_frame.append(pkt)
            if pkt.marker:  # Marker bit indicates end of frame
                frames.append(current_frame)
                current_frame = []

        # Add any remaining packets as incomplete frame
        if current_frame:
            frames.append(current_frame)

        return frames

    def _decode_frame(self, frame_data: bytes) -> Optional[np.ndarray]:
        """Decode a single video frame.

        Args:
            frame_data: Raw frame bytes

        Returns:
            Numpy array (height, width, channels) or None if decode fails
        """
        if self.params is None:
            raise ValueError("Video parameters not set")

        try:
            if self.params.pixel_format == 'YCbCr-4:2:2':
                return self._decode_422(frame_data)
            elif self.params.pixel_format == 'YCbCr-4:4:4':
                return self._decode_444(frame_data)
            elif self.params.pixel_format == 'RGB':
                return self._decode_rgb(frame_data)
            else:
                raise ValueError(f"Unsupported pixel format: {self.params.pixel_format}")
        except Exception as e:
            # Return None for failed frames
            return None

    def _decode_422(self, data: bytes) -> np.ndarray:
        """Decode YCbCr 4:2:2 frame.

        Args:
            data: Raw frame bytes

        Returns:
            Numpy array (height, width, 3) in YCbCr format
        """
        width, height = self.params.width, self.params.height
        bit_depth = self.params.bit_depth

        if bit_depth == 8:
            # For 8-bit, UYVY packing: U Y V Y (4 bytes for 2 pixels)
            expected_size = width * height * 2
            if len(data) < expected_size:
                # Pad with zeros if data is too short
                data = data + b'\x00' * (expected_size - len(data))

            # Decode UYVY
            uyvy = np.frombuffer(data[:expected_size], dtype=np.uint8)
            uyvy = uyvy.reshape(height, width // 2, 4)

            # Extract Y, U, V components
            y = np.zeros((height, width), dtype=np.uint8)
            u = np.zeros((height, width), dtype=np.uint8)
            v = np.zeros((height, width), dtype=np.uint8)

            y[:, 0::2] = uyvy[:, :, 1]  # Y0
            y[:, 1::2] = uyvy[:, :, 3]  # Y1
            u[:, 0::2] = uyvy[:, :, 0]  # U
            u[:, 1::2] = uyvy[:, :, 0]  # U (duplicate)
            v[:, 0::2] = uyvy[:, :, 2]  # V
            v[:, 1::2] = uyvy[:, :, 2]  # V (duplicate)

            # Stack into YCbCr image
            frame = np.stack([y, u, v], axis=2)

        elif bit_depth == 10:
            # 10-bit 4:2:2 is more complex, typically packed
            # For simplicity, treat as 16-bit and scale down
            expected_size = width * height * 2 * 2  # 2 components per pixel, 2 bytes each
            if len(data) < expected_size:
                data = data + b'\x00' * (expected_size - len(data))

            # Simplified 10-bit decode - read as 16-bit big-endian
            pixels = np.frombuffer(data[:expected_size], dtype='>u2')
            pixels = (pixels >> 6).astype(np.uint8)  # Convert 10-bit to 8-bit

            # Reshape and separate components (simplified)
            frame = pixels.reshape(height, width, 2)
            # Expand to 3 channels by duplicating chroma
            y = frame[:, :, 0:1]
            c = frame[:, :, 1:2]
            frame = np.concatenate([y, c, c], axis=2)

        else:
            raise ValueError(f"Unsupported bit depth for 4:2:2: {bit_depth}")

        return frame

    def _decode_444(self, data: bytes) -> np.ndarray:
        """Decode YCbCr 4:4:4 frame.

        Args:
            data: Raw frame bytes

        Returns:
            Numpy array (height, width, 3) in YCbCr format
        """
        width, height = self.params.width, self.params.height
        bit_depth = self.params.bit_depth

        expected_size = width * height * 3 * ((bit_depth + 7) // 8)

        if len(data) < expected_size:
            data = data + b'\x00' * (expected_size - len(data))

        if bit_depth == 8:
            pixels = np.frombuffer(data[:expected_size], dtype=np.uint8)
            frame = pixels.reshape(height, width, 3)
        else:
            # For 10/12-bit, read as 16-bit and scale
            pixels = np.frombuffer(data[:expected_size], dtype='>u2')
            pixels = (pixels >> (bit_depth - 8)).astype(np.uint8)
            frame = pixels.reshape(height, width, 3)

        return frame

    def _decode_rgb(self, data: bytes) -> np.ndarray:
        """Decode RGB frame.

        Args:
            data: Raw frame bytes

        Returns:
            Numpy array (height, width, 3) in RGB format
        """
        width, height = self.params.width, self.params.height
        bit_depth = self.params.bit_depth

        expected_size = width * height * 3 * ((bit_depth + 7) // 8)

        if len(data) < expected_size:
            data = data + b'\x00' * (expected_size - len(data))

        if bit_depth == 8:
            pixels = np.frombuffer(data[:expected_size], dtype=np.uint8)
            frame = pixels.reshape(height, width, 3)
        else:
            # For 10/12-bit, read as 16-bit and scale
            pixels = np.frombuffer(data[:expected_size], dtype='>u2')
            pixels = (pixels >> (bit_depth - 8)).astype(np.uint8)
            frame = pixels.reshape(height, width, 3)

        return frame

    def get_video_info(self) -> dict:
        """Get information about decoded video.

        Returns:
            Dictionary with video information
        """
        if self.params is None or not self.frames:
            return {}

        return {
            'width': self.params.width,
            'height': self.params.height,
            'pixel_format': self.params.pixel_format,
            'bit_depth': self.params.bit_depth,
            'frame_rate': self.params.frame_rate,
            'interlaced': self.params.interlaced,
            'num_frames': len(self.frames),
            'duration_seconds': len(self.frames) / self.params.frame_rate,
            'resolution': f"{self.params.width}x{self.params.height}"
        }
