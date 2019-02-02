#!/usr/bin/env python
# -*- coding: utf-8 -*-


from scapy.all import *
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6
from scapy.layers.inet import TCP
from scapy.layers.inet import UDP

import queue
import threading
import time
import yaml
import logging
import logging.config


class Messenger(threading.Thread):
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
        self.stop = threading.Event()
        with open("logger.yml") as conf_fn:
            self.conf = conf_fn.read()
        self.conf = yaml.load(self.conf)
        logging.config.dictConfig(self.conf)
        self.logger = logging.getLogger('myason_agent')

    def run(self):
        self.logger.info('Messenger: up and running...')
        while not self.stop.isSet():
            try:
                msg = self.messages.get(block=False)
                if msg is not None:
                    self.process_message(msg)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.logger.info('Messenger: stopping...')
        self.clean_up()
        super().join(timeout)
        self.logger.info('Messenger: stopped...')

    def clean_up(self):
        self.logger.info('Messenger: processing remaining messages...')
        while True:
            try:
                pkt = self.messages.get(block=False)
                if pkt is not None:
                    self.process_message(pkt)
            except queue.Empty:
                break

    def process_message(self, msg):
        if msg[0] == 'DEBUG':
            self.logger.debug(msg[1])
        elif msg[0] == 'INFO':
            self.logger.info(msg[1])
        elif msg[0] == 'WARNING':
            self.logger.warning(msg[1])
        elif msg[0] == 'ERROR':
            self.logger.error(msg[1])
        elif msg[0] == 'CRITICAL':
            self.logger.critical(msg[1])
        else:
            self.logger.debug(msg[1])


class Processor(threading.Thread):
    def __init__(self, packets, messages):
        super().__init__()
        self.packets = packets
        self.messages = messages
        self.stop = threading.Event()
        self.cache = {}
        self.cache_limit = 1024
        self.active_timeout = 1800
        self.inactive_timeout = 15

    def run(self):
        self.messages.put(("INFO", "Processor: up and running..."))
        while not self.stop.isSet():
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", 'Processor: stopping...'))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", "Processor: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", "Processor: cleaning up the packets queue..."))
        while True:
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                break
        self.messages.put(("INFO", "Processor: packets queue has been cleaned..."))

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
            sport = 0
            dport = 0
            flags = None
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
        if len(self.cache) > self.cache_limit:
            # Export oldest entry
            self.messages.put(("WARNING", "Processor: Cache size exceeded. Verify settings..."))
            cache_temp = sorted(((self.cache[key]["start_time"], key) for key in self.cache.keys()))
            entry = {cache_temp[0][1]: self.cache.pop(cache_temp[0][1], None)}
            self.messages.put(("DEBUG", entry))
        cache_temp = dict(self.cache)
        for key_field in cache_temp.keys():
            start_time = cache_temp[key_field]["start_time"]
            end_time = cache_temp[key_field]["end_time"]
            flags = cache_temp[key_field]["flags"]
            aged = False
            if self.stop.is_set():
                # Export the entry as the agent exits
                aged = True
            elif 'F' in flags or 'R' in flags:
                # Export the entry as TCP session is closed
                aged = True
            elif end_time - start_time > self.active_timeout:
                # Export the entry because of max activity
                aged = True
            elif time.time() - end_time > self.inactive_timeout:
                # Export the entry because of max inactivity
                aged = True
            if aged:
                entry = {key_field: self.cache.pop(key_field, None)}
                self.messages.put(("DEBUG", entry))


class Sniffer(threading.Thread):
    def __init__(self, pkts, messages, interface=None):
        super().__init__()
        self.daemon = True
        self.socket = None
        self.interface = interface
        self.stop = threading.Event()
        self.pkts = pkts
        self.messages = messages

    def run(self):
        self.socket = conf.L2listen(
                type=ETH_P_ALL,
                iface=self.interface,
        )
        self.messages.put(("INFO", "Sniffer: up and running..."))
        sniff(
                opened_socket=self.socket,
                prn=self.process_packet,
                stop_filter=self.should_stop_sniffer
        )

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", 'Sniffer: stopping...'))
        super().join(timeout)
        self.messages.put(("INFO", "Sniffer: stopped..."))

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
            time.sleep(100)
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
