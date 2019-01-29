#!/usr/bin/env python
# -*- coding: utf-8 -*-
import queue

from scapy.all import *
from scapy.layers.l2 import Ether

from threading import Thread, Event
from queue import Queue
from time import sleep


class Processor(Thread):
    def __init__(self, packets):
        super().__init__()
        self._packets = packets
        self._stop_processor = Event()

    def run(self):
        print("[!] Packet processor is up and running...")
        while not self._stop_processor.isSet():
            print("[!] {} packets in queue...".format(self._packets.qsize()))
            try:
                pkt = self._packets.get(block=False)
                if pkt is not None:
                    self._process_packet(pkt)
            except queue.Empty:
                time.sleep(1)

    def join(self, timeout=None):
        self._stop_processor.set()
        self._clean_up()
        print("[!] Packet processor is stopped...")
        super().join(timeout)

    def _clean_up(self):
        print("[!] Cleaning up the queue...")
        while True:
            try:
                pkt = self._packets.get(block=False)
                if pkt is not None:
                    self._process_packet(pkt)
            except queue.Empty:
                break
        print("[!] Queue has been cleaned...")

    @staticmethod
    def _process_packet(pkt):
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
        print("[!] Sniffer is up and running...")
        sniff(
                opened_socket=self.socket,
                prn=self._process_packet,
                stop_filter=self._should_stop_sniffer
        )

    def join(self, timeout=None):
        self.stop_sniffer.set()
        print("[!] Sniffer is stopped...")
        super().join(timeout)

    def _should_stop_sniffer(self, _):
        return self.stop_sniffer.isSet()

    def _process_packet(self, pkt):
        if Ether in pkt:
            self.pkts.put(pkt)


def agent():
    pkt_queue = Queue()
    processor = Processor(pkt_queue)
    processor.start()
    sniffer = Sniffer(pkt_queue, interface=None)
    sniffer.start()
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        sniffer.join()
        if sniffer.isAlive():
            sniffer.socket.close()
        processor.join()


def main():
    agent()


if __name__ == '__main__':
    main()
