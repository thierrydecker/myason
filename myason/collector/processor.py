# -*- coding: utf-8 -*-


import threading
import queue
import time
import json
import base64
import binascii


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
        try:
            # Decode base 64
            data = base64.b64decode(data)
            # Decode bytes
            data = data.decode()
            # Build a dictionary from json string
            data = dict(json.loads(data))
        except (binascii.Error, UnicodeError, json.JSONDecodeError) as e:
            self.messages.put(("WARNING", f"{self.name}: {e} Record {data} received from {ip} was ignored!"))
            return
        # Data received sanity checks
        flow_ids = list(data.keys())
        for flow_id in flow_ids:
            try:
                length = int(data[flow_id]["bytes"])
                packets = data[flow_id]["packets"]
                start_time = data[flow_id]["start_time"]
                end_time = data[flow_id]["end_time"]
                flags = data[flow_id]["flags"]
                flow = {
                    flow_id: {
                        "bytes": length,
                        "packets": packets,
                        "start_time": start_time,
                        "end_time": end_time,
                        'flags': flags,
                    }
                }
                self.entries.put((ip, flow))
            except (KeyError, ValueError) as e:
                self.messages.put(("WARNING", f"{self.name}: {e} flow {flow_id} received from {ip} was ignored!"))
