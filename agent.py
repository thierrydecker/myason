#!/usr/bin/env python
# -*- coding: utf-8 -*-
import queue

from scapy.all import *
from scapy.layers.l2 import Ether

from threading import Thread, Event
from queue import Queue
from time import sleep


class Processor(Thread):
    def __init__(self, packets, stop_processor):
        super().__init__()
        self.packets = packets
        self.stop_processor = stop_processor

    def run(self):
        while not self.stop_processor.isSet():
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                time.sleep(0.5)
        while True:
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                break

    @staticmethod
    def process_packet(pkt):
        if Ether in pkt:
            layer = pkt.getlayer(Ether)
            print("[>] src={}, dst={}, type={}".format(layer.src, layer.dst, layer.type))


class Sniffer(Thread):
    def __init__(self, pkts, interface=None):
        super().__init__()
        self.daemon = True
        self.socket = None
        self.interface = interface
        self.stop_sniffer = Event()
        self.pkts = pkts

    def run(self):
        self.socket = conf.L2listen(
                type=ETH_P_ALL,
                iface=self.interface,
        )
        sniff(
                opened_socket=self.socket,
                prn=self.process_packet,
                stop_filter=self.should_stop_sniffer
        )

    def join(self, timeout=None):
        self.stop_sniffer.set()
        super().join(timeout)

    def should_stop_sniffer(self, _):
        return self.stop_sniffer.isSet()

    def process_packet(self, pkt):
        if Ether in pkt:
            self.pkts.put(pkt)


def agent():
    pkt_queue = Queue()
    stp_prc = Event()
    processor = Processor(pkt_queue, stp_prc)
    processor.start()
    sniffer = Sniffer(pkt_queue, interface=None)
    sniffer.start()
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        sniffer.join(2.0)
        if sniffer.isAlive():
            sniffer.socket.close()
        stp_prc.set()
        processor.join(2.0)


def main():
    agent()


if __name__ == '__main__':
    main()
