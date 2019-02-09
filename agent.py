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
import os
import ifaddr


class Sniffer(threading.Thread):
    worker_group = "sniffer"
    worker_number = 0

    def __init__(self, pkts, messages, interface):
        super().__init__()
        Sniffer.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
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
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while True:
            sniff(
                opened_socket=self.socket,
                prn=self.process_packet,
                stop_filter=self.should_stop_sniffer,
                timeout=1.0
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
        self.messages.put(("DEBUG", f"{self.name}: Received a frame... {pkt.summary()} on '{self.interface}'"))
        if Ether in pkt:
            self.messages.put(("DEBUG", f"{self.name}: Frame is Ethernet..."))
            self.pkts.put(pkt)
            return
        self.messages.put(("DEBUG", f"{self.name}: Frame is NOT Ethernet. Ignoring it..."))


class Messenger(threading.Thread):
    worker_group = "messenger"
    worker_number = 0

    def __init__(self, logger_conf, messages):
        super().__init__()
        Messenger.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.messages = messages
        self.stop = threading.Event()
        self.logger_conf = logger_conf
        logging.config.dictConfig(self.logger_conf)
        self.logger = logging.getLogger("myason_agent")

    def run(self):
        self.logger.info(f"{self.name}: up and running...")
        while not self.stop.isSet():
            try:
                msg = self.messages.get(block=False)
                if msg is not None:
                    self.process_message(msg)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.logger.info(f"{self.name}: stopping...")
        self.clean_up()
        super().join(timeout)
        self.logger.info(f"{self.name}: stopped...")

    def clean_up(self):
        self.logger.info(f"{self.name}: processing remaining messages...")
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


class Exporter(threading.Thread):
    worker_group = "exporter"
    worker_number = 0

    def __init__(self, entries, messages):
        super().__init__()
        Exporter.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.entries = entries
        self.messages = messages
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while not self.stop.isSet():
            try:
                entry = self.entries.get(block=False)
                if entry is not None:
                    self.export_entry(entry)
            except queue.Empty:
                time.sleep(0.5)

    def export_entry(self, entry):
        self.messages.put(("DEBUG", f"{self.name}: {entry}"))

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: cleaning up the entries queue..."))
        while True:
            try:
                entry = self.entries.get(block=False)
                if entry is not None:
                    self.export_entry(entry)
            except queue.Empty:
                break
        self.messages.put(("INFO", f"{self.name}: entries queue has been cleaned..."))


def logger_conf_loader(logger_conf_fn):
    with open(logger_conf_fn) as conf_fn:
        logger_conf = conf_fn.read()
    logger_conf = yaml.load(logger_conf)
    return logger_conf


def agent_conf_loader(agent_conf_fn):
    with open(agent_conf_fn) as conf_fn:
        agent_conf = conf_fn.read()
    agent_conf = yaml.load(agent_conf)
    return agent_conf


def create_logger(name, configuration):
    logging.config.dictConfig(configuration)
    return logging.getLogger(name)


def conf_is_ok(agent_logger_conf_fn, agent_conf_fn):
    #
    # Basic logging configuration
    #
    default_logging = {
        "version": 1,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                'filename': "agent_error.log"
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["file"]
        },
        'disable_existing_loggers': False
    }
    log = create_logger('root', default_logging)
    conf_ok = True
    #
    # Configurations sanity chacks
    #
    log.info("Beginning agent configuration sanity checks...")
    #
    # Agent logger configuration sanity checks
    #
    log.info("Agent logger configuration checks...")
    #
    # Verify agent logger configuration file existance
    #
    log.info(f"Verifying agent logger configuration file ({agent_logger_conf_fn}) existance...")
    if not os.path.exists(agent_logger_conf_fn):
        log.error(f"Configuration file ({agent_logger_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Agent logger configuration file ({agent_logger_conf_fn}) exists...")
    #
    # Try to parse agent logger configuration file
    #
    log.info(f"Parsing agent logger configuration file ({agent_logger_conf_fn})...")
    try:
        with open(agent_logger_conf_fn) as conf_fn:
            agent_logger_conf = conf_fn.read()
        agent_logger_conf = yaml.load(agent_logger_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing agent logger configuration file ({agent_logger_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed agent logger configuration file ({agent_logger_conf_fn})...")
    #
    # Verify agent logger conf is a valid configuration
    #
    log.info(f"Verifying if agent logger configuration file ({agent_logger_conf_fn}) is valid...")
    try:
        create_logger("myason_agent", agent_logger_conf)
    except ValueError as e:
        log = create_logger('root', default_logging)
        log.error(f"Agent logger configuration file ({agent_logger_conf_fn}): {e}... exiting!")
        return False
    log = create_logger('root', default_logging)
    log.info(f"Agent logger configuration file ({agent_logger_conf_fn}) is valid...")
    #
    # Agent configuration sanity checks
    #
    log.info("Agent configuration checks...")
    #
    # Verify agent configuration file existance
    #
    log.info(f"Verifying agent configuration file ({agent_conf_fn}) existance...")
    if not os.path.exists(agent_conf_fn):
        log.error(f"Configuration file ({agent_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Agent configuration file ({agent_conf_fn}) exists...")
    #
    # Try to parse agent configuration file
    #
    log.info(f"Parsing agent configuration file ({agent_conf_fn})...")
    try:
        with open(agent_conf_fn) as conf_fn:
            agent_conf = conf_fn.read()
        agent_conf = yaml.load(agent_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing agent configuration file ({agent_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed agent configuration file ({agent_conf_fn})...")
    #
    # Ckeck agent configuration items
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) items...")
    #
    # Check interfaces item
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) item interfaces...")
    iflist = agent_conf.get("interfaces", None)
    if iflist is None:
        log.error(f"Missing interfaces in agent configuration file ({agent_conf_fn})... Exiting!")
        return False
    if type(iflist) is not list:
        log.error(f"Interfaces in agent configuration file ({agent_conf_fn}) must be a list... Exiting!")
        return False
    #
    # Check interfaces names
    #
    adapters = [ifname.nice_name for ifname in ifaddr.get_adapters()]
    for ifname in iflist:
        if ifname not in adapters:
            log.error(f"Interface {ifname} in agent configuration file ({agent_conf_fn}) is not valid... Exiting!")
    log.info(f"Interfaces in agent configuration file ({agent_conf_fn}) passed...")
    #
    # Exiting sanity checks with the relevant message
    #
    if conf_ok:
        log.info("Agent configuration checks passed...")
        log.info("Starting the agent...")
        return True
    else:
        log.error("Agent configuration checks failed... Exiting!")
        return False


def agent(logger_conf_fn, agent_conf_fn):
    if not conf_is_ok(logger_conf_fn, agent_conf_fn):
        return
    # Load configurations
    logger_conf = logger_conf_loader(logger_conf_fn)
    agent_conf = agent_conf_loader(agent_conf_fn)
    # Create the messages queue
    msg_queue = queue.Queue()
    # Create the messenger worker
    messenger = Messenger(
        logger_conf,
        msg_queue
    )
    # Start a stack of workers for each interface
    interfaces = agent_conf["interfaces"]
    workers_stack = dict()
    for interface in interfaces:
        pkt_queue = queue.Queue()
        ent_queue = queue.Queue()
        workers_stack[interface] = {
            "sniffer": Sniffer(
                pkt_queue,
                msg_queue,
                interface=interface,
            ),
            "processor": Processor(
                pkt_queue,
                ent_queue,
                msg_queue,
                agent_conf.get("cache_limit", 1024),
                agent_conf.get("cache_active_timeout", 1800),
                agent_conf.get("cache_inactive_timeout", 15),
            ),
            "exporter": Exporter(
                ent_queue,
                msg_queue,
            ),
        }
    # Start the messenger worker
    messenger.start()
    # Start the stack of workers
    for interface in interfaces:
        workers_stack[interface]["exporter"].start()
        workers_stack[interface]["processor"].start()
        workers_stack[interface]["sniffer"].start()
    # Infinite loop until KeyBoardInterrupt
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        msg_queue.put(("DEBUG", "KeyBoardInterrupt received. Stopping agent..."))
        # Stop The stack of workers
        for interface in interfaces:
            workers_stack[interface]["sniffer"].join()
            if workers_stack[interface]["sniffer"].isAlive():
                workers_stack[interface]["sniffer"].socket.close()
            workers_stack[interface]["processor"].join()
            workers_stack[interface]["exporter"].join()
        # Stop the messenger worker
        messenger.join()


def main():
    agent(
        logger_conf_fn="agent_logger.yml",
        agent_conf_fn="agent.yml"
    )


if __name__ == "__main__":
    main()
