#!/usr/bin/env python
# -*- coding: utf-8 -*-


import queue

from scapy.all import *

from myason.agent.conf import conf_is_ok
from myason.agent.exporter import Exporter
from myason.agent.processor import Processor
from myason.agent.sniffer import Sniffer
from myason.helpers.conf import conf_loader
from myason.helpers.logging import logger_conf_loader
from myason.helpers.messenger import Messenger


def agent(logger_conf_fn, agent_conf_fn):
    if not conf_is_ok(logger_conf_fn, agent_conf_fn):
        return
    # Load configurations
    logger_conf = logger_conf_loader(logger_conf_fn)
    agent_conf = conf_loader(agent_conf_fn)
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
                ifname=interface,
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
        logger_conf_fn="config/agent_logger.yml",
        agent_conf_fn="config/agent.yml"
    )


if __name__ == "__main__":
    main()
