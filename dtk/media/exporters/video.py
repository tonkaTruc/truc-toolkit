"""Video exporter for MP4, MOV, and other formats using FFmpeg."""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
import numpy as np


class VideoExporter:
    """Export decoded video frames to various formats using FFmpeg."""

    SUPPORTED_FORMATS = ['mp4', 'mov', 'avi', 'mkv']
    SUPPORTED_CODECS = ['h264', 'h265', 'prores', 'prores_ks']

    # ProRes profiles
    PRORES_PROFILES = {
        'proxy': 0,      # ProRes 422 Proxy
        'lt': 1,         # ProRes 422 LT
        'standard': 2,   # ProRes 422
        'hq': 3,         # ProRes 422 HQ
        '4444': 4,       # ProRes 4444
        '4444xq': 5      # ProRes 4444 XQ
    }

    def __init__(self):
        """Initialize video exporter."""
        self.last_export_path: Optional[str] = None

    def export(self, frames: List[np.ndarray], frame_rate: float, output_path: str,
               format: str = 'mp4', codec: str = 'h264', **kwargs) -> str:
        """Export video frames to file.

        Args:
            frames: List of numpy arrays (height, width, channels)
            frame_rate: Frame rate in fps
            output_path: Output file path
            format: Output format ('mp4', 'mov', 'avi', 'mkv')
            codec: Video codec ('h264', 'h265', 'prores', 'prores_ks')
            **kwargs: Additional codec-specific options:
                - crf: Quality for h264/h265 (0-51, lower is better, default 18)
                - preset: Encoding speed for h264/h265 (default 'medium')
                - prores_profile: ProRes profile name (default 'standard')
                - pixel_format: Input pixel format ('rgb', 'yuv422', 'yuv444')

        Returns:
            Path to exported file

        Raises:
            ValueError: If format or codec is not supported
            RuntimeError: If FFmpeg fails
        """
        format = format.lower()
        codec = codec.lower()

        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. "
                           f"Supported: {', '.join(self.SUPPORTED_FORMATS)}")

        if codec not in self.SUPPORTED_CODECS:
            raise ValueError(f"Unsupported codec: {codec}. "
                           f"Supported: {', '.join(self.SUPPORTED_CODECS)}")

        # Ensure output path has correct extension
        output_path = self._ensure_extension(output_path, format)

        # Get frame dimensions
        height, width, channels = frames[0].shape

        # Determine pixel format
        input_pixel_format = kwargs.get('pixel_format', 'rgb')
        if input_pixel_format == 'rgb':
            pix_fmt = 'rgb24'
        elif input_pixel_format == 'yuv422':
            pix_fmt = 'yuv422p'
        elif input_pixel_format == 'yuv444':
            pix_fmt = 'yuv444p'
        else:
            pix_fmt = 'rgb24'  # Default

        # Build FFmpeg command
        ffmpeg_cmd = self._build_ffmpeg_command(
            width, height, frame_rate, pix_fmt, codec, output_path, **kwargs
        )

        # Run FFmpeg
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Write frames to FFmpeg stdin
            for frame in frames:
                # Ensure frame is uint8
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                process.stdin.write(frame.tobytes())

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {stderr.decode('utf-8')}")

        except Exception as e:
            raise RuntimeError(f"Failed to export video: {str(e)}")

        self.last_export_path = output_path
        return output_path

    def _ensure_extension(self, path: str, format: str) -> str:
        """Ensure file path has correct extension.

        Args:
            path: File path
            format: Desired format

        Returns:
            Path with correct extension
        """
        p = Path(path)
        if p.suffix.lower() != f'.{format}':
            return str(p.with_suffix(f'.{format}'))
        return path

    def _build_ffmpeg_command(self, width: int, height: int, frame_rate: float,
                              pix_fmt: str, codec: str, output_path: str,
                              **kwargs) -> List[str]:
        """Build FFmpeg command line.

        Args:
            width: Frame width
            height: Frame height
            frame_rate: Frame rate
            pix_fmt: Input pixel format
            codec: Video codec
            output_path: Output file path
            **kwargs: Additional options

        Returns:
            FFmpeg command as list of arguments
        """
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}',
            '-pix_fmt', pix_fmt,
            '-r', str(frame_rate),
            '-i', '-',  # Read from stdin
        ]

        # Add codec-specific options
        if codec in ['h264', 'h265']:
            cmd.extend(self._get_h26x_options(codec, **kwargs))
        elif codec in ['prores', 'prores_ks']:
            cmd.extend(self._get_prores_options(codec, **kwargs))

        cmd.append(output_path)
        return cmd

    def _get_h26x_options(self, codec: str, **kwargs) -> List[str]:
        """Get H.264/H.265 encoding options.

        Args:
            codec: 'h264' or 'h265'
            **kwargs: Options

        Returns:
            List of FFmpeg arguments
        """
        options = []

        # Codec name
        if codec == 'h264':
            options.extend(['-vcodec', 'libx264'])
        else:  # h265
            options.extend(['-vcodec', 'libx265'])

        # CRF (quality)
        crf = kwargs.get('crf', 18)
        options.extend(['-crf', str(crf)])

        # Preset (encoding speed)
        preset = kwargs.get('preset', 'medium')
        options.extend(['-preset', preset])

        # Pixel format for output
        options.extend(['-pix_fmt', 'yuv420p'])

        return options

    def _get_prores_options(self, codec: str, **kwargs) -> List[str]:
        """Get ProRes encoding options.

        Args:
            codec: 'prores' or 'prores_ks'
            **kwargs: Options

        Returns:
            List of FFmpeg arguments
        """
        options = []

        # Codec name
        if codec == 'prores':
            options.extend(['-vcodec', 'prores'])
        else:  # prores_ks
            options.extend(['-vcodec', 'prores_ks'])

        # ProRes profile
        profile_name = kwargs.get('prores_profile', 'standard')
        profile_num = self.PRORES_PROFILES.get(profile_name, 2)
        options.extend(['-profile:v', str(profile_num)])

        # Pixel format
        if profile_name in ['4444', '4444xq']:
            options.extend(['-pix_fmt', 'yuv444p10le'])
        else:
            options.extend(['-pix_fmt', 'yuv422p10le'])

        # Vendor (for prores_ks)
        if codec == 'prores_ks':
            options.extend(['-vendor', 'apl0'])

        return options

    def get_codec_info(self, codec: str) -> dict:
        """Get information about a codec.

        Args:
            codec: Codec name

        Returns:
            Dictionary with codec information
        """
        codec_info = {
            'h264': {
                'name': 'H.264 / AVC',
                'description': 'Most compatible, good compression',
                'recommended_for': 'Web playback, compatibility',
                'quality_range': '0-51 CRF (lower is better)',
                'recommended_quality': 18,
                'lossless': False
            },
            'h265': {
                'name': 'H.265 / HEVC',
                'description': 'Better compression than H.264',
                'recommended_for': 'High quality, smaller files',
                'quality_range': '0-51 CRF (lower is better)',
                'recommended_quality': 18,
                'lossless': False
            },
            'prores': {
                'name': 'Apple ProRes',
                'description': 'Professional editing codec',
                'recommended_for': 'Video editing, post-production',
                'profiles': list(self.PRORES_PROFILES.keys()),
                'lossless': 'Near-lossless (4444/4444xq can be lossless)'
            },
            'prores_ks': {
                'name': 'Apple ProRes (FFmpeg native)',
                'description': 'FFmpeg native ProRes encoder',
                'recommended_for': 'Video editing without external encoder',
                'profiles': list(self.PRORES_PROFILES.keys()),
                'lossless': 'Near-lossless (4444/4444xq can be lossless)'
            }
        }

        return codec_info.get(codec.lower(), {})

    @staticmethod
    def check_ffmpeg() -> bool:
        """Check if FFmpeg is available.

        Returns:
            True if FFmpeg is installed and accessible
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
