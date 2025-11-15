"""Packet modification utilities for manipulating captured packets.

This module provides utilities for modifying packet fields in packet lists,
useful for anonymizing captures or preparing packets for replay.
"""

import logging
from typing import Optional

from scapy.all import Ether, IP, TCP, UDP, PacketList, wrpcap


logger = logging.getLogger(__name__)


def modify_ip_field(
    packets: PacketList,
    field: str,
    value: str
) -> tuple[int, int]:
    """Modify IP layer field across all packets in a packet list.

    Args:
        packets: PacketList to modify
        field: Field to modify ('src' or 'dst')
        value: New value for the field

    Returns:
        Tuple of (packets_modified, packets_without_layer)
    """
    if field not in ['src', 'dst']:
        raise ValueError(f"Invalid IP field: {field}. Must be 'src' or 'dst'")

    applied_count = 0
    no_layer_count = 0

    for pkt in packets:
        if pkt.haslayer(IP):
            applied_count += 1

            # Set the field
            setattr(pkt[IP], field, value)

            # Recalculate checksums after modification
            del pkt[IP].chksum
            if pkt.haslayer(TCP):
                del pkt[TCP].chksum
            elif pkt.haslayer(UDP):
                del pkt[UDP].chksum
        else:
            logger.debug(f"Packet does not have IP layer: {pkt.summary()}")
            no_layer_count += 1

    return applied_count, no_layer_count


def modify_ethernet_field(
    packets: PacketList,
    field: str,
    value: str
) -> tuple[int, int]:
    """Modify Ethernet layer field across all packets in a packet list.

    Args:
        packets: PacketList to modify
        field: Field to modify ('src' or 'dst')
        value: New value for the field (MAC address)

    Returns:
        Tuple of (packets_modified, packets_without_layer)
    """
    if field not in ['src', 'dst']:
        raise ValueError(f"Invalid Ethernet field: {field}. Must be 'src' or 'dst'")

    applied_count = 0
    no_layer_count = 0

    for pkt in packets:
        if pkt.haslayer(Ether):
            applied_count += 1
            setattr(pkt[Ether], field, value)
        else:
            logger.debug(f"Packet does not have Ethernet layer: {pkt.summary()}")
            no_layer_count += 1

    return applied_count, no_layer_count


def anonymize_packets(
    packets: PacketList,
    zero_ip_src: bool = True,
    zero_ip_dst: bool = False,
    zero_mac_src: bool = True,
    zero_mac_dst: bool = False
) -> PacketList:
    """Anonymize packet addresses by zeroing out specified fields.

    Args:
        packets: PacketList to anonymize
        zero_ip_src: Zero out IP source addresses
        zero_ip_dst: Zero out IP destination addresses
        zero_mac_src: Zero out MAC source addresses
        zero_mac_dst: Zero out MAC destination addresses

    Returns:
        Modified PacketList
    """
    if zero_ip_src:
        modified, skipped = modify_ip_field(packets, 'src', '0.0.0.0')
        logger.info(f"Zeroed IP src on {modified} packets ({skipped} skipped)")

    if zero_ip_dst:
        modified, skipped = modify_ip_field(packets, 'dst', '0.0.0.0')
        logger.info(f"Zeroed IP dst on {modified} packets ({skipped} skipped)")

    if zero_mac_src:
        modified, skipped = modify_ethernet_field(packets, 'src', '00:00:00:00:00:00')
        logger.info(f"Zeroed MAC src on {modified} packets ({skipped} skipped)")

    if zero_mac_dst:
        modified, skipped = modify_ethernet_field(packets, 'dst', '00:00:00:00:00:00')
        logger.info(f"Zeroed MAC dst on {modified} packets ({skipped} skipped)")

    return packets


def save_packets(packets: PacketList, filename: str) -> str:
    """Save packet list to a pcap file.

    Args:
        packets: PacketList to save
        filename: Output filename

    Returns:
        Absolute path to saved file

    Raises:
        ValueError: If packet list is empty
    """
    if not packets:
        raise ValueError("Cannot save empty packet list")

    wrpcap(filename, packets)
    logger.info(f"Saved {len(packets)} packets to {filename}")

    return filename
