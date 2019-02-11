# -*- coding: utf-8 -*-


import threading
import select


class Listener(threading.Thread):
    worker_group = "listener"
    worker_number = 0

    def __init__(self, records, messages, sock, address, port):
        super().__init__()
        Listener.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.records = records
        self.messages = messages
        self.sock = sock
        self.address = address
        self.port = port
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        self.sock.bind((self.address, self.port))
        while not self.stop.isSet():
            rlist, wlist, elist = select.select([self.sock], [], [], 1)
            if rlist:
                for sock in rlist:
                    data, ip = sock.recvfrom(1024)
                    self.messages.put(("DEBUG", f"{self.name}: from {ip} received {data}"))
                    self.records.put((data, ip))

    def join(self, timeout=None):
        self.stop.set()
        self.messages.put(("INFO", f"{self.name}: stopping..."))
        self.clean_up()
        super().join(timeout)
        self.messages.put(("INFO", f"{self.name}: stopped..."))

    def clean_up(self):
        self.messages.put(("INFO", f"{self.name}: processing remaining records..."))
