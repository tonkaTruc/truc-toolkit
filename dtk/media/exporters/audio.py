"""Audio exporter for WAV, FLAC, and MP3 formats."""

import wave
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np


class AudioExporter:
    """Export decoded audio to various file formats."""

    SUPPORTED_FORMATS = ['wav', 'flac', 'mp3']

    def __init__(self):
        """Initialize audio exporter."""
        self.last_export_path: Optional[str] = None

    def export(self, samples: np.ndarray, sample_rate: int, output_path: str,
               format: str = 'wav', bit_depth: int = 24, **kwargs) -> str:
        """Export audio samples to file.

        Args:
            samples: Numpy array of audio samples (channels, samples) in range [-1.0, 1.0]
            sample_rate: Sample rate in Hz
            output_path: Output file path
            format: Output format ('wav', 'flac', 'mp3')
            bit_depth: Bit depth for output (16, 24, 32)
            **kwargs: Additional format-specific options

        Returns:
            Path to exported file

        Raises:
            ValueError: If format is not supported
        """
        format = format.lower()
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. "
                           f"Supported: {', '.join(self.SUPPORTED_FORMATS)}")

        # Ensure output path has correct extension
        output_path = self._ensure_extension(output_path, format)

        if format == 'wav':
            self._export_wav(samples, sample_rate, output_path, bit_depth)
        elif format == 'flac':
            self._export_flac(samples, sample_rate, output_path, bit_depth)
        elif format == 'mp3':
            bitrate = kwargs.get('bitrate', 320)  # Default to 320 kbps
            self._export_mp3(samples, sample_rate, output_path, bitrate)

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

    def _export_wav(self, samples: np.ndarray, sample_rate: int,
                    output_path: str, bit_depth: int = 24):
        """Export to WAV format using standard wave module.

        Args:
            samples: Audio samples (channels, samples)
            sample_rate: Sample rate in Hz
            output_path: Output file path
            bit_depth: Bit depth (16, 24, 32)
        """
        if bit_depth not in [16, 24, 32]:
            raise ValueError(f"Unsupported bit depth for WAV: {bit_depth}")

        # Determine number of channels and samples
        if len(samples.shape) == 1:
            channels = 1
            num_samples = len(samples)
            samples = samples.reshape(1, -1)
        else:
            channels, num_samples = samples.shape

        # Convert to integer samples
        if bit_depth == 16:
            dtype = np.int16
            max_val = 32767
        elif bit_depth == 24:
            dtype = np.int32
            max_val = 8388607
        else:  # 32-bit
            dtype = np.int32
            max_val = 2147483647

        # Clip and convert to integers
        samples_clipped = np.clip(samples, -1.0, 1.0)
        samples_int = (samples_clipped * max_val).astype(dtype)

        # Interleave channels
        if channels > 1:
            samples_int = samples_int.T.flatten()

        # Write WAV file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(bit_depth // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_int.tobytes())

    def _export_flac(self, samples: np.ndarray, sample_rate: int,
                     output_path: str, bit_depth: int = 24):
        """Export to FLAC format using soundfile.

        Args:
            samples: Audio samples (channels, samples)
            sample_rate: Sample rate in Hz
            output_path: Output file path
            bit_depth: Bit depth (16, 24)
        """
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError("soundfile package required for FLAC export. "
                            "Install with: pip install soundfile")

        if bit_depth not in [16, 24]:
            raise ValueError(f"Unsupported bit depth for FLAC: {bit_depth}")

        # soundfile expects (samples, channels) format
        if len(samples.shape) == 1:
            audio_data = samples
        else:
            audio_data = samples.T

        # Determine subtype based on bit depth
        subtype = f'PCM_{bit_depth}'

        sf.write(output_path, audio_data, sample_rate, subtype=subtype, format='FLAC')

    def _export_mp3(self, samples: np.ndarray, sample_rate: int,
                    output_path: str, bitrate: int = 320):
        """Export to MP3 format using FFmpeg.

        Args:
            samples: Audio samples (channels, samples)
            sample_rate: Sample rate in Hz
            output_path: Output file path
            bitrate: MP3 bitrate in kbps
        """
        # First export to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name

        try:
            # Export to WAV first
            self._export_wav(samples, sample_rate, tmp_wav_path, bit_depth=16)

            # Convert to MP3 using FFmpeg
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-i', tmp_wav_path,
                '-codec:a', 'libmp3lame',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                output_path
            ]

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr}")

        finally:
            # Clean up temporary WAV file
            Path(tmp_wav_path).unlink(missing_ok=True)

    def get_format_info(self, format: str) -> dict:
        """Get information about a supported format.

        Args:
            format: Format name

        Returns:
            Dictionary with format information
        """
        format_info = {
            'wav': {
                'name': 'WAV',
                'description': 'Waveform Audio File Format (uncompressed)',
                'supported_bit_depths': [16, 24, 32],
                'lossless': True,
                'requires_ffmpeg': False
            },
            'flac': {
                'name': 'FLAC',
                'description': 'Free Lossless Audio Codec',
                'supported_bit_depths': [16, 24],
                'lossless': True,
                'requires_ffmpeg': False
            },
            'mp3': {
                'name': 'MP3',
                'description': 'MPEG Audio Layer III (lossy compression)',
                'supported_bit_depths': [16],
                'lossless': False,
                'requires_ffmpeg': True,
                'default_bitrate': 320
            }
        }

        return format_info.get(format.lower(), {})
