"""Pcap file replay functionality for network testing.

This module provides utilities to list and replay packet capture files
from the resources/cap_store directory on network interfaces.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

from scapy.all import rdpcap, sendp, send


def get_cap_store_path() -> Path:
    """Get the path to the cap_store directory.

    Returns:
        Path object pointing to Resources/cap_store/
    """
    # Get the project root (assuming this file is in ttk/network/packet/)
    project_root = Path(__file__).parent.parent.parent.parent
    cap_store = project_root / "Resources" / "cap_store"

    if not cap_store.exists():
        raise FileNotFoundError(f"Cap store directory not found: {cap_store}")

    return cap_store


def list_pcaps() -> List[Dict[str, any]]:
    """List all pcap files in the cap_store directory.

    Returns:
        List of dictionaries containing pcap file information:
        - name: filename
        - path: full path to file
        - size: file size in bytes
    """
    cap_store = get_cap_store_path()
    pcap_files = []

    # Search for .pcap and .pcapng files
    for pattern in ["*.pcap", "*.pcapng"]:
        for pcap_file in cap_store.glob(pattern):
            if pcap_file.is_file():
                pcap_files.append({
                    "name": pcap_file.name,
                    "path": str(pcap_file),
                    "size": pcap_file.stat().st_size
                })

    # Sort by name for consistent output
    pcap_files.sort(key=lambda x: x["name"])

    return pcap_files


def get_pcap_path(filename: str) -> Path:
    """Get the full path to a pcap file in cap_store.

    Args:
        filename: Name of the pcap file (can be just filename or full path)

    Returns:
        Path object to the pcap file

    Raises:
        FileNotFoundError: If the pcap file doesn't exist
    """
    # If it's already a full path that exists, use it
    if os.path.isabs(filename) and os.path.exists(filename):
        return Path(filename)

    # Otherwise, look in cap_store
    cap_store = get_cap_store_path()
    pcap_path = cap_store / filename

    if not pcap_path.exists():
        raise FileNotFoundError(f"Pcap file not found: {pcap_path}")

    return pcap_path


def replay_pcap(
    pcap_file: str,
    interface: str,
    layer: int = 2,
    count: Optional[int] = None,
    inter: float = 0,
    verbose: bool = True
) -> int:
    """Replay a pcap file on a network interface.

    Args:
        pcap_file: Name of pcap file in cap_store or full path
        interface: Network interface name to replay on (e.g., 'eth0')
        layer: OSI layer for replay (2 for L2 with Ethernet, 3 for L3 IP only)
        count: Number of packets to replay (None = all packets)
        inter: Time interval between packets in seconds (0 = as fast as possible)
        verbose: Show verbose output during replay

    Returns:
        Number of packets replayed

    Raises:
        FileNotFoundError: If pcap file doesn't exist
        ValueError: If invalid layer specified
    """
    if layer not in [2, 3]:
        raise ValueError(f"Layer must be 2 or 3, got: {layer}")

    # Get the pcap file path
    pcap_path = get_pcap_path(pcap_file)

    # Read the pcap file
    packets = rdpcap(str(pcap_path))

    # Limit packet count if specified
    if count is not None:
        packets = packets[:count]

    packet_count = len(packets)

    # Replay at the specified layer
    if layer == 2:
        # Layer 2 replay (with Ethernet headers)
        sendp(packets, iface=interface, inter=inter, verbose=verbose)
    else:
        # Layer 3 replay (IP only, no Ethernet)
        send(packets, inter=inter, verbose=verbose)

    return packet_count


def get_pcap_info(pcap_file: str) -> Dict[str, any]:
    """Get information about a pcap file.

    Args:
        pcap_file: Name of pcap file in cap_store or full path

    Returns:
        Dictionary containing:
        - name: filename
        - path: full path
        - size: file size in bytes
        - packet_count: number of packets in the file

    Raises:
        FileNotFoundError: If pcap file doesn't exist
    """
    pcap_path = get_pcap_path(pcap_file)
    packets = rdpcap(str(pcap_path))

    return {
        "name": pcap_path.name,
        "path": str(pcap_path),
        "size": pcap_path.stat().st_size,
        "packet_count": len(packets)
    }
