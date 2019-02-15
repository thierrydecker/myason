# -*- coding: utf-8 -*-

import queue
import threading
import time
import json
import base64
from cryptography.fernet import Fernet


class Exporter(threading.Thread):
    worker_group = "exporter"
    worker_number = 0

    def __init__(self, entries, messages, sock, address, port):
        super().__init__()
        Exporter.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.entries = entries
        self.messages = messages
        self.sock = sock
        self.address = address
        self.port = port
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
        self.messages.put(("DEBUG", f"{self.name}: Processing flow entry {entry}"))
        # Marshall entry (a dict()) to a json string
        data = json.dumps(entry)
        self.messages.put(("DEBUG", f"{self.name}: Sending flow entry to ({self.address}, {self.port}): json {data}"))
        # Encode string
        data = data.encode()
        self.messages.put(
            ("DEBUG", f"{self.name}: Sending flow entry to ({self.address}, {self.port}): encoded {data}"))
        # Encode bytes to base 64
        data = base64.b64encode(data)
        self.messages.put(("DEBUG", f"{self.name}: Sending flow entry to ({self.address}, {self.port}): base64 {data}"))
        # Crypt the data
        key = 'raQHLAAWepWDA9rxUCH5sP-FEMnMZ419B4zO7YmyeMI='.encode()
        fernet = Fernet(key)
        data = fernet.encrypt(data)
        self.messages.put(("DEBUG", f"{self.name}: Sending flow entry to ({self.address}, {self.port}): fernet {data}"))
        # Send to collector
        self.sock.sendto(data, (self.address, self.port))

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
        self.sock.close()
