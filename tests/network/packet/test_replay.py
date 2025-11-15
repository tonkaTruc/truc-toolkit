"""Tests for pcap replay functionality."""

import pytest
from pathlib import Path

from ttk.network.packet.replay import (
    get_cap_store_path,
    list_pcaps,
    get_pcap_path,
    get_pcap_info
)


def test_get_cap_store_path():
    """Test that cap_store path exists."""
    cap_store = get_cap_store_path()
    assert cap_store.exists()
    assert cap_store.name == "cap_store"


def test_list_pcaps():
    """Test listing pcap files."""
    pcaps = list_pcaps()

    # Should find at least some pcap files
    assert len(pcaps) > 0

    # Check structure of returned data
    for pcap in pcaps:
        assert 'name' in pcap
        assert 'path' in pcap
        assert 'size' in pcap
        assert pcap['size'] > 0

        # Verify file extensions
        assert pcap['name'].endswith('.pcap') or pcap['name'].endswith('.pcapng')


def test_get_pcap_path_with_filename():
    """Test getting pcap path with just filename."""
    # Get first pcap from list
    pcaps = list_pcaps()
    if not pcaps:
        pytest.skip("No pcap files found in cap_store")

    first_pcap = pcaps[0]['name']
    pcap_path = get_pcap_path(first_pcap)

    assert pcap_path.exists()
    assert pcap_path.name == first_pcap


def test_get_pcap_path_with_full_path():
    """Test getting pcap path with full path."""
    pcaps = list_pcaps()
    if not pcaps:
        pytest.skip("No pcap files found in cap_store")

    full_path = pcaps[0]['path']
    pcap_path = get_pcap_path(full_path)

    assert pcap_path.exists()
    assert str(pcap_path) == full_path


def test_get_pcap_path_nonexistent():
    """Test that nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        get_pcap_path("nonexistent_file.pcap")


def test_get_pcap_info():
    """Test getting pcap file information."""
    pcaps = list_pcaps()
    if not pcaps:
        pytest.skip("No pcap files found in cap_store")

    first_pcap = pcaps[0]['name']
    info = get_pcap_info(first_pcap)

    assert 'name' in info
    assert 'path' in info
    assert 'size' in info
    assert 'packet_count' in info

    assert info['name'] == first_pcap
    assert info['size'] > 0
    assert info['packet_count'] > 0


# Note: replay_pcap() tests would require root privileges and a valid network interface
# These should be tested manually or in an integration test environment with proper setup
