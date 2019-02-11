# -*- coding: utf-8 -*-

import logging
import logging.config
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
