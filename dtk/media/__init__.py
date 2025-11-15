"""Media processing module for SMPTE ST 2110 flows.

This module provides functionality for:
- RTP stream extraction and reassembly
- ST 2110-20 (video) decoding
- ST 2110-30 (audio) decoding
- ST 2110-40 (ancillary data) decoding
- Media export to various formats
"""

from .rtp_extractor import RTPStreamExtractor

__all__ = ['RTPStreamExtractor']
