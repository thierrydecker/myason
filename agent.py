#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scapy.all import *
from scapy.layers.l2 import Ether

from threading import Thread, Event
from time import sleep


class Sniffer(Thread):
    def __init__(self, interface=None):
        super().__init__()
        self.daemon = True
        self.socket = None
        self.interface = interface
        self.stop_sniffer = Event()

    def run(self):
        self.socket = conf.L2listen(
                type=ETH_P_ALL,
                iface=self.interface,
        )
        sniff(
                opened_socket=self.socket,
                prn=self.print_packet,
                stop_filter=self.should_stop_sniffer
        )

    def join(self, timeout=None):
        self.stop_sniffer.set()
        super().join(timeout)

    def should_stop_sniffer(self, _):
        return self.stop_sniffer.isSet()

    @staticmethod
    def print_packet(pkt):
        if Ether in pkt:
            layer = pkt.getlayer(Ether)
            print("[!] src={}, dst={}, type={}".format(layer.src, layer.dst, layer.type))


def agent():
    sniffer = Sniffer()
    print("[*] Start sniffing...")
    sniffer.start()
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        print("[*] Stop sniffing")
        sniffer.join(2.0)
        if sniffer.isAlive():
            sniffer.socket.close()
        print("[*] Sniffer stopped")


def main():
    agent()


if __name__ == '__main__':
    main()
