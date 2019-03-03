#!/usr/bin/env python
# -*- coding: utf-8 -*-


import queue
import socket
import time

from myason.collector.conf import conf_is_ok
from myason.collector.listener import Listener
from myason.collector.processor import Processor
from myason.collector.writer import Writer
from myason.helpers.conf import conf_loader
from myason.helpers.logging import logger_conf_loader
from myason.helpers.messenger import Messenger


def collector(logger_conf_fn, collector_conf_fn):
    if not conf_is_ok(logger_conf_fn, collector_conf_fn):
        return
    # Load configurations
    logger_conf = logger_conf_loader(logger_conf_fn)
    collector_conf = conf_loader(collector_conf_fn)
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Create the messages queue
    msg_queue = queue.Queue()
    # Create the entries queue
    ent_queue = queue.Queue()
    # Create the records queue
    rec_queue = queue.Queue()
    # Create the messenger worker
    messenger = Messenger(logger_conf, msg_queue)
    # Create a stack of workers
    writers_number = collector_conf.get("writers_number", 1)
    writers = []
    processors_number = collector_conf.get("processors_number", 1)
    processors = []
    # Create writers
    for n in range(writers_number):
        writers.append(
            Writer(
                entries=ent_queue,
                messages=msg_queue,
                dbname=collector_conf.get("db_name"),
                influx_params=collector_conf.get("influx_params")
            )
        )
    # Create processors
    for n in range(processors_number):
        processors.append(
            Processor(
                agents=collector_conf.get("agents"),
                records=rec_queue,
                entries=ent_queue,
                messages=msg_queue,
                token_ttl=collector_conf.get("token_ttl", 5)
            )
        )
    # Create the listener worker
    listener = Listener(
        records=rec_queue,
        messages=msg_queue,
        sock=sock,
        address=collector_conf.get("bind_address", "127.0.0.1"),
        port=collector_conf.get("bind_port", 9999),
        agents=collector_conf.get("agents", {}),
    )
    # Start the messenger worker
    messenger.start()
    # Start writers
    for writer in writers:
        writer.start()
    # Start processors
    for processor in processors:
        processor.start()
    # Start the listener worker
    listener.start()
    # Infinite loop until KeyBoardInterrupt
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        msg_queue.put(("DEBUG", "KeyBoardInterrupt received. Stopping agent..."))
        # Stop the listener worker
        listener.join()
        # Stop the processor workers
        for processor in processors:
            processor.join()
        # Stop the writer workers
        for writer in writers:
            writer.join()
        # Stop the messenger worker
        messenger.join()


def main():
    collector(
        logger_conf_fn="config/collector_logger.yml",
        collector_conf_fn="config/collector.yml"
    )


if __name__ == '__main__':
    main()
