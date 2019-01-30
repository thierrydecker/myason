#!/usr/bin/env python
# -*- coding: utf-8 -*-


import queue

from scapy.all import *
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP
from scapy.layers.inet import TCP
from scapy.layers.inet import UDP

from threading import Thread, Event
from queue import Queue
from time import sleep


class Messenger(Thread):
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
        self.stop = Event()

    def run(self):
        while not self.stop.isSet():
            try:
                msg = self.messages.get(block=False)
                if msg is not None:
                    self.process_message(msg)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.clean_up()
        super().join(timeout)

    def clean_up(self):
        while True:
            try:
                pkt = self.messages.get(block=False)
                if pkt is not None:
                    self.process_message(pkt)
            except queue.Empty:
                break

    @staticmethod
    def process_message(msg):
        print("{}".format(msg))


class Processor(Thread):
    def __init__(self, packets, messages):
        super().__init__()
        self.packets = packets
        self.messages = messages
        self.stop = Event()
        self.cache = {}

    def run(self):
        self.messages.put("Packets processor is up and running...")
        while not self.stop.isSet():
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.clean_up()
        self.messages.put("Packet processor is stopped...")
        super().join(timeout)

    def clean_up(self):
        self.messages.put("Cleaning up the packets queue...")
        while True:
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                break
        self.messages.put("The packets queue has been cleaned...")

    def process_packet(self, pkt):
        # IP fields
        src_ip = None
        dst_ip = None
        proto = None
        tos = None
        raw_length = None
        length = None
        # TCP/UDP fields
        sport = None
        dport = None
        # TCP fields
        flags = None
        if IP in pkt:
            layer = pkt.getlayer(IP)
            src_ip = layer.src
            dst_ip = layer.dst
            proto = layer.proto
            tos = layer.tos
            raw_length = len(raw(pkt))
            length = layer.len
            if TCP in pkt:
                layer = pkt.getlayer(TCP)
                sport = layer.sport
                dport = layer.dport
                flags = layer.flags
            if UDP in pkt:
                layer = pkt.getlayer(UDP)
                sport = layer.sport
                dport = layer.dport
            flow_id = ','.join((src_ip, dst_ip, str(sport), str(dport), str(proto), str(tos)))
            self.messages.put("flow_id={}".format(flow_id))
            self.messages.put(
                    "src_ip={}, dst_ip={}, proto={}, tos={}, raw_length={}, length={}, sport={}, dport={}, "
                    "flags={}".format(
                            src_ip, dst_ip, proto, tos, raw_length, length, sport, dport, flags
                    )
            )


class Sniffer(Thread):
    def __init__(self, pkts, messages, interface=None):
        super().__init__()
        self.daemon = True
        self.socket = None
        self.interface = interface
        self.stop = Event()
        self.pkts = pkts
        self.messages = messages

    def run(self):
        self.socket = conf.L2listen(
                type=ETH_P_ALL,
                iface=self.interface,
        )
        self.messages.put("Sniffer is up and running...")
        sniff(
                opened_socket=self.socket,
                prn=self.process_packet,
                stop_filter=self.should_stop_sniffer
        )

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put("Sniffer is stopped...")
        super().join(timeout)

    def should_stop_sniffer(self, _):
        return self.stop.isSet()

    def process_packet(self, pkt):
        if Ether in pkt:
            self.pkts.put(pkt)


def agent():
    msg_queue = Queue()
    messenger = Messenger(msg_queue)
    messenger.start()
    pkt_queue = Queue()
    processor = Processor(pkt_queue, msg_queue)
    processor.start()
    sniffer = Sniffer(pkt_queue, msg_queue, interface=None)
    sniffer.start()
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        sniffer.join()
        if sniffer.isAlive():
            sniffer.socket.close()
        processor.join()
        messenger.join()


def main():
    agent()


if __name__ == '__main__':
    main()
