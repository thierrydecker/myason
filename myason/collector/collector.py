#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import queue
import socket
import time

import yaml

from myason.collector.listener import Listener
from myason.collector.messenger import Messenger
from myason.collector.processor import Processor
from myason.collector.writer import Writer
from myason.helpers.logging import create_logger
from myason.helpers.logging import logger_conf_loader


def conf_is_ok(collector_logger_conf_fn, collector_conf_fn):
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
                'filename': "collector_error.log"
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
    log.info("Beginning collector configuration sanity checks...")
    #
    # Collector logger configuration sanity checks
    #
    log.info("Collector logger configuration checks...")
    #
    # Verify collector logger configuration file existance
    #
    log.info(f"Verifying collector logger configuration file ({collector_logger_conf_fn}) existance...")
    if not os.path.exists(collector_logger_conf_fn):
        log.error(f"Configuration file ({collector_logger_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Collector logger configuration file ({collector_logger_conf_fn}) exists...")
    #
    # Try to parse collector logger configuration file
    #
    log.info(f"Parsing collector logger configuration file ({collector_logger_conf_fn})...")
    try:
        with open(collector_logger_conf_fn) as conf_fn:
            collector_logger_conf = conf_fn.read()
        collector_logger_conf = yaml.load(collector_logger_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing collector logger configuration file ({collector_logger_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed collector logger configuration file ({collector_logger_conf_fn})...")
    #
    # Verify collector logger conf is a valid configuration
    #
    log.info(f"Verifying if collector logger configuration file ({collector_logger_conf_fn}) is valid...")
    try:
        create_logger("myason_collector", collector_logger_conf)
    except ValueError as e:
        log = create_logger('root', default_logging)
        log.error(f"Collector logger configuration file ({collector_logger_conf_fn}): {e}... exiting!")
        return False
    log = create_logger('root', default_logging)
    log.info(f"Collector logger configuration file ({collector_logger_conf_fn}) is valid...")
    #
    # Collector configuration sanity checks
    #
    log.info("Collector configuration checks...")
    #
    # Verify collector configuration file existance
    #
    log.info(f"Verifying collector configuration file ({collector_conf_fn}) existance...")
    if not os.path.exists(collector_conf_fn):
        log.error(f"Configuration file ({collector_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Collector configuration file ({collector_conf_fn}) exists...")
    #
    # Try to parse agent configuration file
    #
    log.info(f"Parsing collector configuration file ({collector_conf_fn})...")
    try:
        with open(collector_conf_fn) as conf_fn:
            collector_conf = conf_fn.read()
        yaml.load(collector_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing collector configuration file ({collector_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed collector configuration file ({collector_conf_fn})...")
    #
    # Exiting sanity checks with the relevant message
    #
    log.info("Collector configuration checks passed...")
    log.info("Starting the collector...")
    return True


def collector_conf_loader(collector_conf_fn):
    with open(collector_conf_fn) as conf_fn:
        collector_conf = conf_fn.read()
    collector_conf = yaml.load(collector_conf)
    return collector_conf


def collector(logger_conf_fn, collector_conf_fn):
    if not conf_is_ok(logger_conf_fn, collector_conf_fn):
        return
    # Load configurations
    logger_conf = logger_conf_loader(logger_conf_fn)
    collector_conf = collector_conf_loader(collector_conf_fn)
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
        writers.append(Writer(ent_queue, msg_queue))
    # Create processors
    for n in range(processors_number):
        processors.append(Processor(rec_queue, ent_queue, msg_queue))
    # Create the listener worker
    listener = Listener(rec_queue,
                        msg_queue,
                        sock,
                        collector_conf.get("bind_address", "127.0.0.1"),
                        collector_conf.get("bind_port", 9999),
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
        logger_conf_fn="collector_logger.yml",
        collector_conf_fn="collector.yml"
    )


if __name__ == '__main__':
    main()
