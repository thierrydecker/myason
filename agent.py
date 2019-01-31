#!/usr/bin/env python
# -*- coding: utf-8 -*-


from scapy.all import *
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6
from scapy.layers.inet import TCP
from scapy.layers.inet import UDP

import queue
from threading import Thread, Event
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
        self.cache_limit = 500
        self.active_timeout = 180
        self.inactive_timeout = 60

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
        # Packets dissection
        if IP in pkt:
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            proto = pkt[IP].proto
            tos = pkt[IP].tos
            length = pkt[IP].len
        elif IPv6 in pkt:
            src_ip = pkt[IPv6].src
            dst_ip = pkt[IPv6].dst
            proto = pkt[IPv6].nh
            tos = pkt[IPv6].tc
            length = pkt[IPv6].plen
        else:
            return
        if TCP in pkt:
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
            flags = pkt[TCP].flags
        elif UDP in pkt:
            sport = pkt[UDP].sport
            dport = pkt[UDP].dport
            flags = None
        else:
            return
        key_field = f"{src_ip},{dst_ip},{proto},{sport},{dport},{tos}"
        # Cache management
        if key_field in self.cache:
            # Update cache entry
            self.cache[key_field]["bytes"] += length
            self.cache[key_field]["packets"] += 1
            self.cache[key_field]["end_time"] = time.time()
            self.cache[key_field]["flags"] = str(flags)
        else:
            # Add cache entry
            non_key_fields = {
                "bytes": length,
                "packets": 1,
                "start_time": time.time(),
                "end_time": time.time(),
                "flags": str(flags),
            }
            self.cache[key_field] = non_key_fields
        # Cache aging
        cache_temp = dict(self.cache)
        for key_field in cache_temp.keys():
            start_time = cache_temp[key_field]["start_time"]
            end_time = cache_temp[key_field]["end_time"]
            flags = cache_temp[key_field]["flags"]
            aged = False
            reason = 'Unknow'
            if self.stop.is_set():
                aged = True
                reason = 'Stop asked'
            elif len(cache_temp) > self.cache_limit:
                aged = True
                reason = 'Cache limit'
            elif 'F' in flags or 'R' in flags:
                aged = True
                reason = 'TCP end session'
            elif end_time - start_time > self.active_timeout:
                aged = True
                reason = 'Active timeout'
            elif time.time() - end_time > self.inactive_timeout:
                aged = True
                reason = 'Inactive timeout'
            if aged:
                self.messages.put(
                        "Reason=" + reason + " - " + key_field + " - " + str(self.cache.pop(key_field, None))
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
    msg_queue = queue.Queue()
    pkt_queue = queue.Queue()
    messenger = Messenger(msg_queue)
    messenger.start()
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
