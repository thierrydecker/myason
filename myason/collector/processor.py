# -*- coding: utf-8 -*-


import threading
import queue
import time


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
                rec = self.records.get(block=False)
                if rec is not None:
                    self.process_record(rec)
            except queue.Empty:
                time.sleep(0.5)

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: processing remaining records..."))
        while True:
            try:
                rec = self.records.get(block=False)
                if rec is not None:
                    self.process_record(rec)
            except queue.Empty:
                break

    def process_record(self, record):
        data, ip = record
        self.messages.put(("DEBUG", f"{self.name}: Processing record {data} received from {ip}"))
