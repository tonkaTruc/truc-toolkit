"""Packet construction utilities using Scapy best practices."""

import logging

from scapy.layers.inet import Ether, IP, UDP, TCP
from scapy.layers.rtp import RTP
from scapy.packet import Packet


class PacketBuilder:
	"""Builder class for constructing network packets layer by layer."""

	def __init__(self, src_mac=None, dst_mac=None):
		"""Initialize packet builder with optional Ethernet addresses.

		Args:
			src_mac (str, optional): Source MAC address. Defaults to all zeros.
			dst_mac (str, optional): Destination MAC address. Defaults to all zeros.
		"""
		self.log = logging.getLogger(__name__)
		self.packet = Ether(
			src=src_mac or "00:00:00:00:00:00",
			dst=dst_mac or "00:00:00:00:00:00"
		)
		self.log.debug("Initialized Ethernet layer")

	def add_ip(self, src=None, dst=None, **kwargs):
		"""Add IP layer to packet.

		Args:
			src (str, optional): Source IP address
			dst (str, optional): Destination IP address
			**kwargs: Additional IP layer parameters

		Returns:
			PacketBuilder: Self for method chaining
		"""
		ip_layer = IP(**kwargs)
		if src:
			ip_layer.src = src
		if dst:
			ip_layer.dst = dst

		self.packet = self.packet / ip_layer
		self.log.debug(f"Added IP layer: {src} -> {dst}")
		return self

	def add_udp(self, sport=None, dport=None, **kwargs):
		"""Add UDP layer to packet.

		Args:
			sport (int, optional): Source port
			dport (int, optional): Destination port
			**kwargs: Additional UDP layer parameters

		Returns:
			PacketBuilder: Self for method chaining
		"""
		udp_layer = UDP(**kwargs)
		if sport:
			udp_layer.sport = sport
		if dport:
			udp_layer.dport = dport

		self.packet = self.packet / udp_layer
		self.log.debug(f"Added UDP layer: {sport} -> {dport}")
		return self

	def add_tcp(self, sport=None, dport=None, **kwargs):
		"""Add TCP layer to packet.

		Args:
			sport (int, optional): Source port
			dport (int, optional): Destination port
			**kwargs: Additional TCP layer parameters

		Returns:
			PacketBuilder: Self for method chaining
		"""
		tcp_layer = TCP(**kwargs)
		if sport:
			tcp_layer.sport = sport
		if dport:
			tcp_layer.dport = dport

		self.packet = self.packet / tcp_layer
		self.log.debug(f"Added TCP layer: {sport} -> {dport}")
		return self

	def add_rtp(self, **kwargs):
		"""Add RTP layer to packet.

		Args:
			**kwargs: RTP layer parameters

		Returns:
			PacketBuilder: Self for method chaining
		"""
		self.packet = self.packet / RTP(**kwargs)
		self.log.debug("Added RTP layer")
		return self

	def add_payload(self, data):
		"""Add payload data to packet.

		Args:
			data (bytes or str): Payload data

		Returns:
			PacketBuilder: Self for method chaining
		"""
		if isinstance(data, str):
			data = data.encode()
		self.packet = self.packet / data
		self.log.debug(f"Added payload ({len(data)} bytes)")
		return self

	def build(self) -> Packet:
		"""Build and return the final packet.

		Returns:
			Packet: The constructed Scapy packet
		"""
		return self.packet

	def to_bytes(self) -> bytes:
		"""Convert packet to bytes.

		Returns:
			bytes: Raw packet bytes
		"""
		return bytes(self.packet)

	def show(self):
		"""Display packet structure."""
		self.packet.show()


if __name__ == "__main__":
	# Example usage
	logging.basicConfig(level=logging.DEBUG)

	# Build a simple UDP packet
	pkt = PacketBuilder()
	pkt.add_ip(src="192.168.1.100", dst="192.168.1.1")
	pkt.add_udp(sport=5000, dport=5001)
	pkt.add_payload("Hello, World!")

	print("\nConstructed packet:")
	pkt.show()

	print(f"\nPacket type: {type(pkt.build())}")
	print(f"Packet bytes length: {len(pkt.to_bytes())}")