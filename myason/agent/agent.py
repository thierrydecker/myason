#!/usr/bin/env python
# -*- coding: utf-8 -*-


import queue

import ifaddr
import yaml
from scapy.all import *

from myason.agent.exporter import Exporter
from myason.agent.messenger import Messenger
from myason.agent.processor import Processor
from myason.agent.sniffer import Sniffer
from myason.helpers.logging import create_logger
from myason.helpers.logging import logger_conf_loader


def agent_conf_loader(agent_conf_fn):
    with open(agent_conf_fn) as conf_fn:
        agent_conf = conf_fn.read()
    agent_conf = yaml.load(agent_conf)
    return agent_conf


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
        log.info(f"Checking agent configuration file ({agent_conf_fn}) interfaces names...")
        if ifname not in adapters:
            log.error(
                f"Interface {ifname} in agent configuration file ({agent_conf_fn}), {ifname} is not valid... Exiting!"
            )
    log.info(f"Interfaces in agent configuration file ({agent_conf_fn}) passed...")
    #
    # Ckeck socket creation
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) socket creation...")
    collector_address = agent_conf.get("collector_address", "127.0.0.1")
    collector_port = agent_conf.get("collector_port", 9999)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(str("Test").encode(), (collector_address, collector_port))
    except OverflowError:
        log.error(
            f"Interfaces in agent configuration file ({agent_conf_fn}), collector_port={collector_port} invalid..."
        )
        return False
    except socket.gaierror:
        log.error(
            f"Interfaces in agent configuration file ({agent_conf_fn}), collector_address={collector_address} invalid..."
        )
        return False
    #
    # Exiting sanity checks with the relevant message
    #
    log.info("Agent configuration checks passed...")
    log.info("Starting the agent...")
    return True


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
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
                sock,
                agent_conf.get("collector_address", "127.0.0.1"),
                agent_conf.get("collector_port", 9999),
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
