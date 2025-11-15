import json
import logging
import os
import socket
import time

import netifaces2 as netifaces
import psutil
from scapy.all import (
    Ether,
    IP,
    UDP,
    TCP,
    RTP,
    Raw,
    sniff,
    rdpcap,
    wrpcap,
    sendp,
    send,
    ls,
    hexdump,
    get_if_list,
    get_windows_if_list,
)
from ttk.custom_headers.PTP import ieee1588

packet_counter = 0
current_rtp_time = 0
rtp_stamps = []


class pkt_craft:

	def __init__(self, capture_interface=None, replay_interface=None):

		# Configure the host network adapter to use
		print("Configure capture interface")
		self.capture_interface = configure_interface(capture_interface)
		logging.debug("Capture interface set as: %s" % self.capture_interface)
		
		print("Configure replay interface")
		self.replay_interface = configure_interface(replay_interface)
		logging.debug("Replay interface set as: %s" % self.capture_interface)


		# Get hostname
		self.hostname = socket.gethostname()

		self.current_pcap = None

		print("\nHost info:")
		print("Hostname: \t\t\t{}".format(self.hostname))
		print("Assigned capture NIC: \t\t{}".format(self.capture_interface))
		print("Assigned replay NIC: \t\t{}".format(self.replay_interface))
		print(130*"-")

	def capture(self, pkt_count=None):

		global packet_counter
		packet_counter = 0

		def count_capture(pkt):
			global packet_counter
			packet_counter += 1

			return "%s %s" % (packet_counter, pkt.summary())

		# cap = sniff(iface=interface, count=int(pkt_count), prn= lambda x: x.nsummary())
		# cap = sniff(iface=interface, count=int(pkt_count), prn=count_capture)
		# cap = sniff(iface=interface, count=int(pkt_count), prn=self.on_rx)
		try:
			cap = sniff(iface=self.capture_interface["name"], count=int(pkt_count), prn=count_capture)
		except KeyboardInterrupt:
			return False

		self.current_pcap = cap

		return cap

	def force_rtp(self):
		"""Iterate through self.capture and force all UDP packets to decode as RTP"""

		no_raw = 0
		rtp_detected = 0
		for pkt in self.current_pcap:
			# Force UDP payload to be interpreted as RTP
			if pkt.haslayer(UDP):
				try:
					pkt[UDP].payload = RTP(pkt[Raw].load)
				except IndexError:
					no_raw += 1
					print(pkt.summary)

			if RTP in pkt:
				rtp_detected += 1

		print("\nNumber of packets decoded as RTP: %s" % rtp_detected)
		print("Number of packets that do not contain raw data: %s" % no_raw)

	def get_rtp_timestamps(self):

		valid_pkt_num = 0
		valid_timestamp = []
		previous_stamp = 0

		no_rtp_pkt = 0

		for pkt in self.current_pcap:
			if pkt.haslayer(RTP):
				valid_pkt_num += 1
				valid_timestamp.append(pkt[RTP].timestamp)
			else:
				no_rtp_pkt += 0

		for stamp in valid_timestamp:

			current_stamp = stamp
			delta = current_stamp - previous_stamp
			previous_stamp = stamp

			print(stamp, delta)

		"""
		previous = 0
		total_stamp = 0
		delta = 0
		for stamp in rtp_stamps:
			total_stamp = total_stamp + stamp
			delta = stamp
			delta = delta - previous
			previous = stamp

		print("Delta (average) = %s" % delta)
		print("Total RTP time stamps = %s" % total_stamp)
		print("Mean = %s" % (total_stamp / len(rtp_stamps)))

		----------------------

		if pkt.haslayer(UDP):
			udp = pkt[UDP]

		if pkt.haslayer(TCP):
			tcp = pkt[TCP]

		"""

	def on_rx(self, pkt):
		global packet_counter
		packet_counter += 1

		global current_rtp_time
		global rtp_stamps

		# print(pkt.show())
		# print("\n" + str(pkt[Raw]))
		if IP in pkt:
			pkt[IP].dst = "0.0.0.0"
			# Recalculate checksum after modification
			del pkt[IP].chksum
			if TCP in pkt:
				del pkt[TCP].chksum
			elif UDP in pkt:
				del pkt[UDP].chksum
		
		# Force UDP payload to be interpreted as RTP
		if UDP in pkt:
			pkt[UDP].payload = RTP(pkt[Raw].load)
				
		if RTP in pkt:
			pkt[RTP].payload_type = 97
			# print(pkt[RTP].timestamp)
			
			if pkt[RTP].timestamp != current_rtp_time:
				print(pkt[RTP].timestamp)
				current_rtp_time = pkt[RTP].timestamp
				rtp_stamps.append(pkt[RTP].timestamp)
			else:
				print(".")
				
		return pkt.summary()

	def inspect(self, **kwargs):
		i = None

		if kwargs.get("mode") == "iterate":
			pkt_start_num = input("Enter packet number to start inspection: ")
			for p in self.current_pcap[int(pkt_start_num):]:

				# Check for PTP layer if needed
				if p.haslayer(ieee1588):
					logging.debug("Packet contains IEEE1588 PTP layer")

				print(90 * "-")
				p.show()
				hexdump(p)
				print(90 * "-")

				menu = [
					"Exit to menu: \"exit\"",
					"Next packet: <Enter>",
					"Alter the packet: \"change\"",
				]

				print(" | ".join(x for x in menu))
				i = input("[CMD]:")

				# Escape the loop back to menu
				if i == "exit":
					self.menu()
				elif i == "change":
					self.manipulate(p)
				else:
					continue

	def manipulate(self, pkt):
		print(pkt.summary())
		packet_info = ls(pkt)
		print(type(packet_info))
		print("\n\n")

		print(pkt[Ether])
		print(pkt[IP])

		print(pkt[Ether].hide_defaults())
		print(pkt[IP].hide_defaults())

		manipulation_opt = {
			"1": "Zero all source values"
		}
		for k, v in manipulation_opt.items():
			print(k, v)
		usr_opt = input("Enter manipulation preset: ")

		if usr_opt == "1":

			# Attempt to reset IP and MAC source addresses
			try:
				print("IP src was: {}".format(pkt[IP].src))
				pkt[IP].src = "0.0.0.0"
				print("IP src now: {}".format(pkt[IP].src))

				# Recalculate checksums after IP modification
				del pkt[IP].chksum
				if pkt.haslayer(TCP):
					del pkt[TCP].chksum
				elif pkt.haslayer(UDP):
					del pkt[UDP].chksum
			except IndexError as err:
				logging.warning(err)

			try:
				print("\nMAC src was: {}".format(pkt[Ether].src))
				pkt[Ether].src = "00:00:00:00:00:00"
				print("MAC src now: {}".format(pkt[Ether].src))
			except IndexError as err:
				logging.warning(err)

		print("Layer 2: src {}\t dst {}".format(pkt[Ether].src, pkt[Ether].dst))
		print("Layer 3: src {}\t\t dst {}".format(pkt[IP].src, pkt[IP].dst))
		print(pkt.command())

		print(pkt.summary())

	def export_capture(self, file):

		# Exit to menu if active cap file is empty
		if not self.current_pcap:
			logging.error("Active cap file is empty... nothing to export")
			raise TypeError("Cannot save empty capture variable!")

		print("Exporting current .pcap var: {}".format(self.current_pcap))
		wrpcap(file, self.current_pcap)
		print("File saved as: {}".format(os.path.abspath(file)))

		return file

	def import_capture(self, file=None):
		cap_store_path = os.path.abspath(os.curdir) + "/cap_store/"

		if not file:
			while True:
				print("Listing directory:\t%s\n" % cap_store_path)

				for item in os.listdir(cap_store_path):
					print("\t- %s" % item)

				target_filename = input("\nEnter filename of target capture: ")
				file = os.path.abspath(cap_store_path + target_filename)

				if os.path.exists(file):
					break
				else:
					logging.error("File does not exist: %s " % file)
					pass

		try:
			cap = rdpcap(file)
		except FileNotFoundError as err:
			print("File supplied for input does not exist: %s" % file)
			return False

		cap.nsummary()

		self.current_pcap = cap

	def menu(self):
		while True:
			print("\nCurrent capture file stats:\t{} ({})".format(self.current_pcap, type(self.current_pcap)))
			print("Capture interface:\t\t%s\n" % self.capture_interface)
			print("Replay interface:\t\t%s\n" % self.replay_interface)
			"""
			Adding new options to menu: 
				Additional menu options can be added by adding them to <menu_options> list.
				The position in the list is reflected in its corresponding option number for user entry
			"""

			menu_options = [
				"Export current .pcap",
				"Produce new .pcap",
				"Import .pcap from drive",
				"Apply global changes to current capture",
				"Inspect cap file",
				"Filter current .pcap",
				"Replay current .pcap"
			]

			for item, num in zip(menu_options, [x for x in range(0, len(menu_options))]):
				print("\t%s: %s" % (num, item))
			usr_opt = input("\nEnter option number: ")

			# Export current .pcap file
			if usr_opt == "0":
				try:
					self.export_capture(input("Enter filname: "))
				except TypeError as err:
					print("You must import or generate a capture in order to save a capture!")
				continue

			if usr_opt == "1":
				print("Capturing from currently selected interface...")
				count = input("Enter number of packets to capture: ")
				self.capture(count)
				continue

			elif usr_opt == "2":
				self.import_capture(input("Enter path or press enter to list default directory: "))
				continue
		
			# Apply global to packets
			elif usr_opt == "3":
				print(" ")
				
				def global_pkt_change(layer, param, value):
					"""Iterate through every packet in self.capture and apply global settings based on arguments
					provided

					:argument layer
					:type string

					:argument param
					:type string

					:argument value
					:type string
					"""
					no_layer_count = 0
					applied_count = 0

					# If cmd begins "ip"
					if layer.lower() == "ip":
						for pkt in self.current_pcap:
							if pkt.haslayer(IP):
								applied_count += 1

								if param.lower() == "src":
									pkt[IP].src = value
								elif param.lower() == "dst":
									pkt[IP].dst = value

								# Recalculate checksums after modification
								del pkt[IP].chksum
								if pkt.haslayer(TCP):
									del pkt[TCP].chksum
								elif pkt.haslayer(UDP):
									del pkt[UDP].chksum
							else:
								logging.info("Packet does not have IP layer: %s" % pkt.summary)
								no_layer_count += 1

						print("Parameters applied to %s packets. %s packets did not contain the target layer and have "
								"not been changed" % (applied_count, no_layer_count))

						return layer, param, value

					# If cmd begins "eth"
					elif layer.lower() == "eth":
						for pkt in self.current_pcap:
							if pkt.haslayer(Ether):
								applied_count += 1

								if param.lower() == "src":
									pkt[Ether].src = value
								elif param.lower() == "dst":
									pkt[Ether].dst = value
							else:
								logging.info("Packet does not have Ethernet layer: %s" % pkt.summary)
								no_layer_count += 1

						print("Parameters applied to %s packets. %s packets did not contain the target layer and have "
								"not been changed" % (applied_count, no_layer_count))

						return layer, param, value

				cmd_list = []
				print("<ip src 0.0.0.0 / eth src 00:00:00:00:00:00>")
				while True:
					cmd = input("Enter global packet parameters. \"end\" to exit: ")
					
					if cmd == "end":
						break
					
					cmd_list.append(cmd)
						
				for cmd in cmd_list:
					if len(cmd.split(" ")) == 3:
						layer, param, value = cmd.split(" ")
						print("\nApplying settings: %s" % cmd)
						global_pkt_change(layer, param, value)
					else:
						print("Incorrectly formatted cmd: \t%s" % cmd)
				continue

			elif usr_opt == "4":
				self.inspect(mode="iterate")
				continue

			elif usr_opt == "5":

				print("\"force rtp\": Force all UDP packets to be decoded as RTP protocol"
						"\"get rtp timestamps\": Calculate delta between all valid RTP packets")

				cmd_list = []

				while True:
					cmd = input("Enter filter commands. \"end\" to exit and apply: ")

					if cmd == "end":
						break

					cmd_list.append(cmd)

				for cmd in cmd_list:
					if cmd == "force rtp":
						self.force_rtp()
					elif cmd == "get rtp timestamps":
						self.get_rtp_timestamps()
					else:
						print("Unrecognised command: %s" % cmd)

				continue

			elif usr_opt == "6":
				replay_opts = [
					"Layer 2 replay (with Ethernet headers)",
					"Layer 3 replay (IP only, no Ethernet)"
				]
				print(" ")
				for opt, num in zip(replay_opts, [x for x in range(0, len(replay_opts))]):
					print("\t%s: %s" % (num, opt))

				usr_opt = input("\nSelect replay type: ")

				if usr_opt == "0":
					# Layer 2 replay with Ethernet headers
					print(f"Replaying {len(self.current_pcap)} packets on interface {self.replay_interface['name']}")
					sendp(self.current_pcap, iface=self.replay_interface["name"], verbose=True)
				elif usr_opt == "1":
					# Layer 3 replay (IP packets only)
					print(f"Replaying {len(self.current_pcap)} packets at layer 3")
					send(self.current_pcap, verbose=True)
				else:
					print(f"Invalid option: {usr_opt}")

				continue


def configure_interface(interface=None):
	"""Gather list of available network interfaces and return NIC information in dict format"""

	if os.name == "nt":
		print("Running Windows")
		
		# Produce a dict of interface names and guid values for all interfaces
		available_interfaces = {name["name"]: name["guid"] for name in get_windows_if_list()}
		
		nic_info = {}
		
		for int_name, int_guid in available_interfaces.items():
			try:
				nic_info[int_name] = netifaces.ifaddresses(int_guid)[netifaces.AF_INET][0]
				nic_info[int_name].update({"guid": int_guid})
				nic_info[int_name].update({"name": int_name})
			except ValueError as err:
				print(err)
				print("Failure ocurred during interface: %s %s" % (int_name, int_guid))
				print("\nInterface data:\n")
				print(json.dumps(nic_info, indent=2))
			except KeyError:
				print("No IPv4 address assigned to NIC %s" % int_name)
		
	elif os.name == "posix":
		print("Running Linux")
		available_interfaces = [x for x in get_if_list()]

		nic_info = {}

		for int_name in available_interfaces:
			try:
				nic_info[int_name] = netifaces.ifaddresses(int_name)[netifaces.AF_INET][0]
				nic_info[int_name].update({"guid": None})
				nic_info[int_name].update({"name": int_name})
			except KeyError:
				print("No IPv4 address assigned to NIC %s... " % int_name)
	else:
		nic_info = None
		quit()

	if not interface:
		interface = input("Enter interface name: ")

	for nic, info in nic_info.items():
		try:
			if nic == interface:
				return info
		except TypeError:
			print(info)
			if interface == nic:
				print("Nic info type is {}".format(type(info)))
				return info
			else:
				logging.error("Failed to find nic dict")

if __name__ == "__main__":

	# Training room
	# krft = pkt_craft("Mellanox ConnectX-5 Adapter #2", "Mellanox ConnectX-5 Adapter")

	krft = pkt_craft()
	krft.menu()

