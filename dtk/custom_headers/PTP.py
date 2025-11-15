from scapy.layers.l2 import Ether
from scapy.all import IP, UDP
from scapy.packet import Packet, bind_layers
from scapy.fields import *
from custom_headers.erspan import *


class ieee1588(Packet):
	name = "Precision Time Protocol"

	fields_desc = [
		XBitField('transportSpecific', 0x1, 4),        # 4 bits
		XBitField('messageType', 0x0, 4),              # 4 bits
		XByteField('versionPTP', 0x05),               # 4 bits
		XShortField('messageLength', 0x0036),      # 2 bytes (what is fmt=H)
		XByteField('subdomainNumber', 0x00),
		XByteField('dummy1', 0x00),
		XShortField('flags', 0x0208),                    # 2 bytes

		# Correction for <SYNC> incorrect
		XBitField('correction', 0x00000000, 64),                 # 64 bits
		XBitField('dummy2', 0x00, 32),
		XBitField('ClockIdentity', 0x08028efffe9b97a5, 64),
		XShortField('SourcePortId', 0x0002),
		XShortField('sequenceId', 0x0566),               # 2 bytes
		XByteField('control', 0x05),                    # 1 byte
		XByteField('logMessagePeriod', 0x7F),     # 1 byte
		XBitField('originTimestamp_s', 0x00, 48),
		XBitField('originTimestamp_ns', 0x00, 32),

		# # DELAY_RESP
		# XBitField('requestingSourcePortIdentity', 0x00, 64),
		# XBitField('requestingSourcePortId', 0x00, 16)

		# XBitField('dummy3', 0x00, 80),
		# XBitField('originCurrentUTCOffset', 0x00, 8)
		# XByteField('dummy4', 0x00)
		# XBitField('priority1', 0x0, 4)

		# XBitField('requestTimestampSec', 0x00000000057b, 48),
		# XBitField('requestTimestampNanoSec', 0x0d11715c, 32),
		# XShortField('requestingSourcePortId', 0x002)
	]


bind_layers(Ether, ieee1588, type="0x88F7")
bind_layers(UDP, ieee1588)
