import logging
import socket
import struct

from dtk.network.interfaces import create_socket, get_best_interface_for


class MulticastMgr:

    def __init__(self, switch_ip: str):

        self.log = logging.getLogger("__name__")
        self.local_ip = get_best_interface_for(switch_ip)
        self.sock = create_socket(self.local_ip, 9989)
        self.log.info(f"Using interface: {self.local_ip}:{self.sock}")

        # Set multicast interface to local_ip
        self.sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(self.local_ip)
        )

        # Set multicast time-to-live to 2...
        # keep our multicast packets from escaping the local network
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    def join(self, multicast_ip):
        """Construct a membership request and send to socket to join a
        multicast group"""

        mreq = struct.pack(
            "4sl",
            socket.inet_aton(multicast_ip),
            socket.INADDR_ANY
        )
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def leave(self, multicast_ip):
        """Construct a membership request and send to socket to leave a
        multicast group"""

        mreq = struct.pack(
            "4sl",
            socket.inet_aton(multicast_ip),
            socket.INADDR_ANY
        )
        self.sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_DROP_MEMBERSHIP,
            mreq
        )

    def display_traffic(self):
        while True:
            print(self.sock.recv(1))
