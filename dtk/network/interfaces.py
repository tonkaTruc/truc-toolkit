import re
import socket
import struct
import sys
from typing import Dict

import psutil

ADDR_FAMILY_MAP = {
    socket.AF_INET: "IPv4",
    socket.AF_INET6: "IPv6",
}

# AF_PACKET (Linux) or AF_LINK (macOS/BSD)
if hasattr(socket, "AF_PACKET"):
    ADDR_FAMILY_MAP[socket.AF_PACKET] = "MAC"
if hasattr(socket, "AF_LINK"):
    ADDR_FAMILY_MAP[socket.AF_LINK] = "MAC"


def create_interfaces_dict() -> Dict[str, Dict]:
    """Generate a dict of available network interfaces on this host.

    Returns:
        Dict: Information for all available host network interfaces
    """

    interfaces = {}
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for iface, addr_list in addrs.items():
        iface_data = {
            "addresses": [],
            "is_up": stats[iface].isup if iface in stats else None,
            "speed_mbps": stats[iface].speed if iface in stats else None,
            "mtu": stats[iface].mtu if iface in stats else None,
        }

        for addr in addr_list:
            iface_data["addresses"].append({
                "family": ADDR_FAMILY_MAP.get(addr.family, "-1"),
                "address": addr.address,
                "netmask": addr.netmask,
                "broadcast": addr.broadcast,
                "ptp": addr.ptp,
            })

        interfaces[iface] = iface_data

    return interfaces


def create_socket(ip: str, port: int) -> socket.socket:
    """An open socket bound to the specified ip and port.

    Args:
        ip (str): IP address to bind
        port (int): Port to bind

    Returns:
        socket.socket: The created socket
    """

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Allow reuse of addresses
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # If you bind to a specific interface on the Mac, no multicast data.
    # If you try to bind to all interfaces on Windows, no multicast data.
    # Hence we check if running on macos before binding the socket.
    # TODO: system detection should be handled at a higher level
    is_macos = sys.platform.startswith("darwin") is True
    sock.bind(('0.0.0.0', port)) if is_macos else sock.bind((ip, port))
    return sock


def ip_is_local(ip_string) -> bool:
    """Uses a regex to determine if the input ip is on a local network.

    It's safe here, but never use a regex for IP verification if from
    a potentially dangerous source.
    """

    # If the regex matches then the ip is likely to be a local ip
    local_ip = "(^10.)|(^172.1[6-9].)|(^172.2[0-9].)|(^172.3[0-1].)|(^192.168.)"
    return re.match(local_ip, ip_string) is not None


def get_best_interface_for(addr):
    """Create a temp socket and use that to connect to an endpoint.
    Return the local nic IP address that made the connection"""

    tmp_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        tmp_s.connect((addr, 9))
        # Get the interface used by the socket.
        local_ip = tmp_s.getsockname()[0]
    except socket.error:
        local_ip = "127.0.0.1"  # FIXME: Temp fix
    finally:
        tmp_s.close()

    return local_ip


def get_interface_ip(interface_name: str) -> str:
    """Get the IPv4 address for a given network interface.

    Args:
        interface_name: Name of the network interface (e.g., 'eth0')

    Returns:
        str: IPv4 address of the interface

    Raises:
        ValueError: If interface not found or has no IPv4 address
    """
    interfaces = create_interfaces_dict()

    if interface_name not in interfaces:
        available = ', '.join(interfaces.keys())
        raise ValueError(
            f"Interface '{interface_name}' not found. "
            f"Available interfaces: {available}"
        )

    # Find the IPv4 address
    for addr in interfaces[interface_name]['addresses']:
        if addr['family'] == 'IPv4':
            return addr['address']

    raise ValueError(
        f"Interface '{interface_name}' has no IPv4 address configured"
    )


def print_stream_info(socket):

    # Data waits on socket buffer until we retrieve it.
    # TODO: filter it out traffic if it came from the current machine.

    # Test Var
    multicast_ip = "239.1.2.3"

    packet = socket.recvfrom(2624)

    # packet tuple to string
    packet = packet[0]

    # Take first 20 characters as IP header
    ip_header = packet[0:20]

    iph = struct.unpack('!BBHHHBBH4s4s' , ip_header)

    version_ihl = iph[0]
    version = version_ihl >> 4
    ihl = version_ihl & 0xF
    iph_length = ihl * 4
    protocol = iph[6]

    u = iph_length
    udph_length = 8
    udp_header = packet[u:u+udph_length]

    # now unpack them :)
    udph = struct.unpack('!HHHH' , udp_header)

    source_port = udph[0]
    dest_port = udph[1]

    if protocol == 17:
        protocol = 'UDP'

    src_addr = socket.inet_ntoa(iph[8])
    dst_addr = socket.inet_ntoa(iph[9])

    if dst_addr == multicast_ip:
        print('\nMulticast stream detected!')
        print('\nProtocol: \t\t', protocol)
        print('Source Port: \t\t', source_port, '\nDestination Port: \t', dest_port)
        print('Source Address: \t', src_addr, '\nDestination Address: \t', dst_addr)
        print('\nCheck wireshark to ensure the correct packets are reaching your NIC\n')
        return True

    else:
        print('No Multicast stream present at: ', multicast_ip)
        return False
