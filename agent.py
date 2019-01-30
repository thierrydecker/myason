#!/usr/bin/env python
# -*- coding: utf-8 -*-


import queue

from scapy.all import *
from scapy.layers.inet import IP

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
        if IP in pkt:
            layer = pkt.getlayer(IP)
            self.messages.put("src={}, dst={}, proto={}".format(layer.src, layer.dst, layer.proto))


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
        if IP in pkt:
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
