import logging
import socket
from pathlib import Path
from typing import Callable, Optional

from scapy.all import PacketList, sniff, wrpcap
from scapy.error import Scapy_Exception


class PackerCaptor:

    def __init__(self, capture_int=None):
        self.log = logging.getLogger("__name__")
        self.interface = capture_int
        self.hostname = socket.gethostname()
        self.log.info(f"{self.hostname}: {self.interface}")

    def capture_traffic(self, count=15, cb: None | Callable = None, save_to: Optional[str] = None) -> PacketList:
        """Capture and print live traffic on the specified interface

        Args:
            count (_type_, optional): Number of packets to capture. Defaults to 15.
            cb (Callable, optional): Optional callback function to process each packet.
            save_to (str, optional): Filename to save captured packets. If provided, saves to cap_store directory.

        Returns:
            PacketList: List of captured packets
        """

        try:
            p_list = sniff(
                iface=self.interface,
                count=count,
                prn=lambda pkt: pkt.summary() if cb is None else cb(pkt),
            )
        except Scapy_Exception as err:
            self.log.error(err)
            raise

        # Save to file if requested
        if save_to:
            self.save_capture(p_list, save_to)

        return p_list

    def save_capture(self, packets: PacketList, filename: str) -> Path:
        """Save captured packets to a pcap file in the cap_store directory.

        Args:
            packets: PacketList to save
            filename: Name of the file to save (will be saved in cap_store directory)

        Returns:
            Path to the saved file

        Raises:
            FileNotFoundError: If cap_store directory doesn't exist
        """
        # Get the cap_store path (Resources/cap_store)
        project_root = Path(__file__).parent.parent.parent.parent
        cap_store = project_root / "Resources" / "cap_store"

        # Create cap_store directory if it doesn't exist
        cap_store.mkdir(parents=True, exist_ok=True)

        # Ensure filename has .pcap extension
        if not filename.endswith(('.pcap', '.pcapng')):
            filename = f"{filename}.pcap"

        # Full path to save file
        save_path = cap_store / filename

        # Save the packets
        wrpcap(str(save_path), packets)
        self.log.info(f"Saved {len(packets)} packets to {save_path}")

        return save_path
