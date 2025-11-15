import os
from pathlib import Path

import pytest
from scapy.layers.l2 import Ether
from scapy.all import rdpcap

from tests import log
from dtk.network.packet.capture import PackerCaptor


@pytest.fixture
def packet_captor() -> PackerCaptor:
    return PackerCaptor(capture_int="en1")


@pytest.fixture
def temp_cap_store(tmp_path):
    """Create a temporary cap_store directory for testing."""
    cap_store = tmp_path / "Resources" / "cap_store"
    cap_store.mkdir(parents=True)
    return cap_store


def test_packet_captor_init(packet_captor):
    assert isinstance(packet_captor, PackerCaptor)
    assert packet_captor.interface == "en1"


def test_packet_captor_print_live_traffic(packet_captor):
    log.info(f"Printing 20 packets of live traffic on {packet_captor.interface}")
    pkts = packet_captor.capture_traffic(
        count=20,
        cb=lambda pkt: log.warning(pkt.summary())
    )
    assert len(pkts) == 20
    for pkt in pkts:
        assert isinstance(pkt, Ether)


def test_packet_captor_save_capture(packet_captor):
    """Test saving captured packets to a pcap file."""
    log.info(f"Capturing 10 packets on {packet_captor.interface} and saving to file")

    # Capture packets with save option
    filename = "test_capture.pcap"
    pkts = packet_captor.capture_traffic(count=10, save_to=filename)

    # Verify packets were captured
    assert len(pkts) == 10

    # Verify file was created in cap_store
    project_root = Path(__file__).parent.parent.parent.parent
    cap_store = project_root / "Resources" / "cap_store"
    saved_file = cap_store / filename

    assert saved_file.exists(), f"File {saved_file} was not created"

    # Verify saved file contains the same packets
    saved_pkts = rdpcap(str(saved_file))
    assert len(saved_pkts) == len(pkts)

    # Clean up
    if saved_file.exists():
        os.remove(saved_file)


def test_save_capture_auto_extension(packet_captor):
    """Test that .pcap extension is automatically added if missing."""
    log.info("Testing automatic .pcap extension")

    # Capture packets
    pkts = packet_captor.capture_traffic(count=5)

    # Save without extension
    filename = "test_no_ext"
    save_path = packet_captor.save_capture(pkts, filename)

    # Verify .pcap extension was added
    assert save_path.name == "test_no_ext.pcap"
    assert save_path.exists()

    # Verify file can be read
    saved_pkts = rdpcap(str(save_path))
    assert len(saved_pkts) == len(pkts)

    # Clean up
    if save_path.exists():
        os.remove(save_path)
