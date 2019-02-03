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
        self.messages.put(("INFO", "Sniffer: stopping..."))
        super().join(timeout)
        self.messages.put(("INFO", "Sniffer: stopped..."))

    def should_stop_sniffer(self, _):
        return self.stop.isSet()

    def process_packet(self, pkt):
        self.messages.put(("DEBUG", f"Sniffer: Received a frame... {pkt.summary()}"))
        if Ether in pkt:
            self.messages.put(("DEBUG", "Sniffer: Frame is Ethernet..."))
            self.pkts.put(pkt)
            return
        self.messages.put(("DEBUG", "Sniffer: Frame is NOT Ethernet. Ignoring it..."))


class Messenger(threading.Thread):
    def __init__(self, logger_conf, messages):
        super().__init__()
        self.messages = messages
        self.stop = threading.Event()
        self.logger_conf = logger_conf
        logging.config.dictConfig(self.logger_conf)
        self.logger = logging.getLogger("myason_agent")

    def run(self):
        self.logger.info("Messenger: up and running...")
        while not self.stop.isSet():
            try:
                msg = self.messages.get(block=False)
                if msg is not None:
                    self.process_message(msg)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.logger.info("Messenger: stopping...")
        self.clean_up()
        super().join(timeout)
        self.logger.info("Messenger: stopped...")

    def clean_up(self):
        self.logger.info("Messenger: processing remaining messages...")
        while True:
            try:
                pkt = self.messages.get(block=False)
                if pkt is not None:
                    self.process_message(pkt)
            except queue.Empty:
                break

    def process_message(self, msg):
        if "DEBUG" == msg[0]:
            self.logger.debug(msg[1])
        elif "INFO" == msg[0]:
            self.logger.info(msg[1])
        elif "WARNING" == msg[0]:
            self.logger.warning(msg[1])
        elif "ERROR" == msg[0]:
            self.logger.error(msg[1])
        elif "CRITICAL" == msg[0]:
            self.logger.critical(msg[1])
        else:
            self.logger.debug(msg[1])


class Processor(threading.Thread):
    def __init__(self, packets, entries, messages, cache_limit, cache_active_timeout, cache_inactive_timeout):
        super().__init__()
        self.packets = packets
        self.messages = messages
        self.entries = entries
        self.stop = threading.Event()
        self.cache = {}
        self.cache_limit = cache_limit
        self.active_timeout = cache_active_timeout
        self.inactive_timeout = cache_inactive_timeout

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
        self.messages.put(("INFO", "Processor: stopping..."))
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
            self.messages.put(("DEBUG", "Processor: Packet is IPv4..."))
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            proto = pkt[IP].proto
            tos = pkt[IP].tos
            length = pkt[IP].len
        elif IPv6 in pkt:
            self.messages.put(("DEBUG", "Processor: Packet is IPv6..."))
            src_ip = pkt[IPv6].src
            dst_ip = pkt[IPv6].dst
            proto = pkt[IPv6].nh
            tos = pkt[IPv6].tc
            length = pkt[IPv6].plen
        else:
            return
        if TCP in pkt:
            self.messages.put(("DEBUG", "Processor: Datagram is TCP..."))
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
            flags = pkt[TCP].flags
        elif UDP in pkt:
            self.messages.put(("DEBUG", "Processor: Datagram is UDP..."))
            sport = pkt[UDP].sport
            dport = pkt[UDP].dport
            flags = None
        else:
            self.messages.put(("DEBUG", "Processor: Datagram is not TCP or UDP..."))
            sport = 0
            dport = 0
            flags = None
        key_field = f"{src_ip},{dst_ip},{proto},{sport},{dport},{tos}"
        # Cache management
        if key_field in self.cache:
            # Update cache entry
            self.messages.put(("DEBUG", "Processor: Update entry in the cache..."))
            self.cache[key_field]["bytes"] += length
            self.cache[key_field]["packets"] += 1
            self.cache[key_field]["end_time"] = time.time()
            self.cache[key_field]["flags"] = str(flags)
        else:
            # Add cache entry
            self.messages.put(("DEBUG", "Processor: Add entry in the cache..."))
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
                self.messages.put(("DEBUG", "Processor: Deleting entry from cache. Agent ending..."))
                aged = True
            elif "F" in flags or "R" in flags:
                # Export the entry as TCP session is closed
                self.messages.put(("DEBUG", "Processor: Deleting entry from cache. TCP session ended..."))
                aged = True
            elif end_time - start_time > self.active_timeout:
                # Export the entry because of max activity
                self.messages.put(("DEBUG", "Processor: Deleting entry from cache. Flow max active timeout..."))
                aged = True
            elif time.time() - end_time > self.inactive_timeout:
                # Export the entry because of max inactivity
                self.messages.put(("DEBUG", "Processor: Deleting entry from cache. Flow max inactive timeout..."))
                aged = True
            if aged:
                entry = {key_field: self.cache.pop(key_field, None)}
                self.messages.put(("DEBUG", "Processor: Sending entry to exporter..."))
                self.entries.put(entry)


class Exporter(threading.Thread):
    def __init__(self, entries, messages):
        super().__init__()
        self.entries = entries
        self.messages = messages
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", "Exporter: up and running..."))
        while not self.stop.isSet():
            try:
                entry = self.entries.get(block=False)
                if entry is not None:
                    self.export_entry(entry)
            except queue.Empty:
                time.sleep(0.5)

    def export_entry(self, entry):
        self.messages.put(("DEBUG", f"Exporter: {entry}"))

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", "Exporter: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", "Exporter: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", "Exporter: cleaning up the entries queue..."))
        while True:
            try:
                entry = self.entries.get(block=False)
                if entry is not None:
                    self.export_entry(entry)
            except queue.Empty:
                break
        self.messages.put(("INFO", "Exporter: entries queue has been cleaned..."))


def agent(logger_conf, agent_conf):
    msg_queue = queue.Queue()
    pkt_queue = queue.Queue()
    ent_queue = queue.Queue()
    messenger = Messenger(logger_conf, msg_queue)
    messenger.start()
    exporter = Exporter(ent_queue, msg_queue)
    exporter.start()
    processor = Processor(
            pkt_queue,
            ent_queue,
            msg_queue,
            agent_conf["cache_limit"],
            agent_conf["cache_active_timeout"],
            agent_conf["cache_inactive_timeout"],
    )
    processor.start()
    sniffer = Sniffer(pkt_queue, msg_queue, interface=agent_conf["interfaces"][0])
    sniffer.start()
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        msg_queue.put(("DEBUG", "KeyBoardInterrupt received. Stopping agent..."))
        sniffer.join()
        if sniffer.isAlive():
            sniffer.socket.close()
        processor.join()
        exporter.join()
        messenger.join()


def logger_conf_loader(logger_conf_fn="agent_logger.yml"):
    with open(logger_conf_fn) as conf_fn:
        logger_conf = conf_fn.read()
    logger_conf = yaml.load(logger_conf)
    return logger_conf


def agent_conf_loader(agent_conf_fn="agent.yml"):
    with open(agent_conf_fn) as conf_fn:
        agent_conf = conf_fn.read()
    agent_conf = yaml.load(agent_conf)
    return agent_conf


def main():
    logger_conf = logger_conf_loader(logger_conf_fn="agent_logger.yml")
    agent_conf = agent_conf_loader(agent_conf_fn="agent.yml")
    agent(logger_conf=logger_conf, agent_conf=agent_conf)


if __name__ == "__main__":
    main()
