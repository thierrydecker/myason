# -*- coding: utf-8 -*-


from scapy.all import *
from scapy.layers.l2 import Ether


class Sniffer(threading.Thread):
    """The Sniffer

    """
    worker_group = "sniffer"
    worker_number = 0

    def __init__(self, pkts, messages, ifname):
        """Initialization
        
        Args:
            pkts: The thread safe FIFO queue to feed with captured packets 
            messages: The thread safe FIFO queue to feed with logging messages
            ifname: The name of the sniffed interface  
        """
        super().__init__()
        Sniffer.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.daemon = True
        self.socket = None
        self.ifname = ifname
        self.stop = threading.Event()
        self.pkts = pkts
        self.messages = messages

    def run(self):
        self.socket = conf.L2listen(
            type=ETH_P_ALL,
            iface=self.ifname,
        )
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while True:
            sniff(
                opened_socket=self.socket,
                prn=self.process_packet,
                stop_filter=self.should_stop_sniffer,
                timeout=1.0,
                monitor=True
            )
            if self.stop.isSet():
                break

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def should_stop_sniffer(self, _):
        return self.stop.isSet()

    def process_packet(self, pkt):
        self.messages.put(("DEBUG", f"{self.name}: Received a frame... {pkt.summary()} on '{self.ifname}'"))
        if Ether in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Frame is Ethernet..."))
            # Put packet and interface name in the queue
            self.pkts.put((pkt, self.ifname))
            return
        self.messages.put(("DEBUG", f"{self.name}: Frame is NOT Ethernet. Ignoring it..."))
