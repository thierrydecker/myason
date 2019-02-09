#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import logging.config
import os
import yaml
import queue
import threading
import time


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
        self.logger = logging.getLogger("myason_collector")

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


class Writer(threading.Thread):
    worker_group = "writer"
    worker_number = 0

    def __init__(self, entries, messages):
        super().__init__()
        Writer.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.entries = entries
        self.messages = messages
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while not self.stop.isSet():
            try:
                ent = self.entries.get(block=False)
                if msg is not None:
                    self.process_entry(ent)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: processing remaining entries..."))
        while True:
            try:
                ent = self.entries.get(block=False)
                if ent is not None:
                    self.process_entry(ent)
            except queue.Empty:
                break

    def process_entry(self, entry):
        pass


class Processor(threading.Thread):
    worker_group = "processor"
    worker_number = 0

    def __init__(self, records, entries, messages):
        super().__init__()
        Processor.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.records = records
        self.entries = entries
        self.messages = messages
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while not self.stop.isSet():
            try:
                msg = self.records.get(block=False)
                if msg is not None:
                    self.process_record(msg)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: processing remaining recordss..."))
        while True:
            try:
                rec = self.records.get(block=False)
                if rec is not None:
                    self.process_record(rec)
            except queue.Empty:
                break

    def process_record(self, record):
        pass


def create_logger(name, configuration):
    logging.config.dictConfig(configuration)
    return logging.getLogger(name)


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
    conf_ok = True
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
        collector_conf = yaml.load(collector_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing collector configuration file ({collector_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed collector configuration file ({collector_conf_fn})...")
    #
    # Exiting sanity checks with the relevant message
    #
    if conf_ok:
        log.info("Collector configuration checks passed...")
        log.info("Starting the collector...")
        return True
    else:
        log.error("Collector configuration checks failed... Exiting!")
        return False


def logger_conf_loader(logger_conf_fn):
    with open(logger_conf_fn) as conf_fn:
        logger_conf = conf_fn.read()
    logger_conf = yaml.load(logger_conf)
    return logger_conf


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
    # Create the messages queue
    msg_queue = queue.Queue()
    # Create the entries queue
    ent_queue = queue.Queue()
    # Create the records queue
    rec_queue = queue.Queue()
    # Create the messenger worker
    messenger = Messenger(
        logger_conf,
        msg_queue,
    )
    # Start a stack of workers
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
    # Start the messenger worker
    messenger.start()
    # Start writers
    for writer in writers:
        writer.start()
    # Start processors
    for processor in processors:
        processor.start()
    # Infinite loop until KeyBoardInterrupt
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        msg_queue.put(("DEBUG", "KeyBoardInterrupt received. Stopping agent..."))
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
