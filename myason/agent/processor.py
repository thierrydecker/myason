# -*- coding: utf-8 -*-

import queue
import threading
import time

from scapy.layers.inet import IP
from scapy.layers.inet import TCP
from scapy.layers.inet import UDP
from scapy.layers.inet6 import IPv6


class Processor(threading.Thread):
    worker_group = "processor"
    worker_number = 0

    def __init__(self, packets, entries, messages, cache_limit, cache_active_timeout, cache_inactive_timeout):
        super().__init__()
        Processor.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.packets = packets
        self.messages = messages
        self.entries = entries
        self.stop = threading.Event()
        self.cache = {}
        self.cache_limit = cache_limit
        self.active_timeout = cache_active_timeout
        self.inactive_timeout = cache_inactive_timeout

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while not self.stop.isSet():
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: cleaning up the packets queue..."))
        while True:
            try:
                pkt = self.packets.get(block=False)
                if pkt is not None:
                    self.process_packet(pkt)
            except queue.Empty:
                break
        self.messages.put(("INFO", f"{self.name}: packets queue has been cleaned..."))

    def process_packet(self, pkt):
        # Packets dissection
        if IP in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Packet is IPv4..."))
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            proto = pkt[IP].proto
            tos = pkt[IP].tos
            length = pkt[IP].len
        elif IPv6 in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Packet is IPv6..."))
            src_ip = pkt[IPv6].src
            dst_ip = pkt[IPv6].dst
            proto = pkt[IPv6].nh
            tos = pkt[IPv6].tc
            length = pkt[IPv6].plen
        else:
            return
        if TCP in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Datagram is TCP..."))
            sport = pkt[TCP].sport
            dport = pkt[TCP].dport
            flags = pkt[TCP].flags
        elif UDP in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Datagram is UDP..."))
            sport = pkt[UDP].sport
            dport = pkt[UDP].dport
            flags = None
        else:
            self.messages.put(("DEBUG", f"{self.name}: Datagram is not TCP or UDP..."))
            sport = 0
            dport = 0
            flags = None
        key_field = f"{src_ip},{dst_ip},{proto},{sport},{dport},{tos}"
        # Cache management
        if key_field in self.cache:
            # Update cache entry
            self.messages.put(("DEBUG", f"{self.name}: Update entry in the cache..."))
            self.cache[key_field]["bytes"] += length
            self.cache[key_field]["packets"] += 1
            self.cache[key_field]["end_time"] = time.time()
            self.cache[key_field]["flags"] = str(flags)
        else:
            # Add cache entry
            self.messages.put(("DEBUG", f"{self.name}: Add entry in the cache..."))
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
            self.messages.put(("WARNING", f"{self.name}: Cache size exceeded. Verify settings..."))
            cache_temp = sorted(((self.cache[key]["start_time"], key) for key in self.cache.keys()))
            entry = {cache_temp[0][1]: self.cache.pop(cache_temp[0][1], None)}
            self.messages.put(("DEBUG", f"{self.name}: {entry}"))
        cache_temp = dict(self.cache)
        for key_field in cache_temp.keys():
            start_time = cache_temp[key_field]["start_time"]
            end_time = cache_temp[key_field]["end_time"]
            flags = cache_temp[key_field]["flags"]
            aged = False
            if self.stop.isSet():
                # Export the entry as the agent exits
                self.messages.put(("DEBUG", f"{self.name}: Deleting entry from cache. Agent ending..."))
                aged = True
            elif "F" in flags or "R" in flags:
                # Export the entry as TCP session is closed
                self.messages.put(("DEBUG", f"{self.name}: Deleting entry from cache. TCP session ended..."))
                aged = True
            elif end_time - start_time > self.active_timeout:
                # Export the entry because of max activity
                self.messages.put(("DEBUG", f"{self.name}: Deleting entry from cache. Flow max active timeout..."))
                aged = True
            elif time.time() - end_time > self.inactive_timeout:
                # Export the entry because of max inactivity
                self.messages.put(("DEBUG", f"{self.name}: Deleting entry from cache. Flow max inactive timeout..."))
                aged = True
            if aged:
                entry = {key_field: self.cache.pop(key_field, None)}
                self.messages.put(("DEBUG", f"{self.name}: Sending entry to exporter..."))
                self.entries.put(entry)
