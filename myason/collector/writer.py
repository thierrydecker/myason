# -*- coding: utf-8 -*-

import threading
import queue
import time
import uuid
import sqlite3


class Writer(threading.Thread):
    worker_group = "writer"
    worker_number = 0

    def __init__(self, entries, messages, dbname):
        super().__init__()
        Writer.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.entries = entries
        self.messages = messages
        self.dbname = dbname
        self.stop = threading.Event()

    def run(self):
        self.messages.put(("INFO", f"{self.name}: up and running..."))
        while not self.stop.isSet():
            try:
                ent = self.entries.get(block=False)
                if ent is not None:
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
        ip = entry[0]
        flow = entry[1]
        self.messages.put(("DEBUG", f"{self.name}: processing {flow} entry received from {ip}..."))
        # Generate a UUID
        flow_uuid = str(uuid.uuid4())
        self.messages.put(("DEBUG", f"{self.name}: Generated uuid: {flow_uuid}..."))
        agent_address = ip[0]
        for flow_id in flow.keys():
            try:
                # Data extraction
                flow_id_parts = flow_id.split(",")
                ifname = flow_id_parts[0]
                src_ip = flow_id_parts[1]
                dst_ip = flow_id_parts[2]
                proto = flow_id_parts[3]
                src_port = flow_id_parts[4]
                dst_port = flow_id_parts[5]
                tos = flow_id_parts[6]
                length = flow[flow_id]["bytes"]
                packets = flow[flow_id]["packets"]
                start_time = flow[flow_id]["start_time"]
                end_time = flow[flow_id]["end_time"]
                flags = flow[flow_id]["flags"]
                # Sqlite processing
                self.messages.put(("DEBUG", f"{self.name}: Connecting to: {self.dbname}..."))
                connection = sqlite3.connect(self.dbname)
                cursor = connection.cursor()
                with connection:
                    data = {
                        "uuid": flow_uuid,
                        "raw": str(flow),
                        "agent_address": agent_address,
                        "ifname": ifname,
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "proto": proto,
                        "src_port": src_port,
                        "dst_port": dst_port,
                        "tos": tos,
                        "bytes": length,
                        "packets": packets,
                        "start_time": start_time,
                        "end_time": end_time,
                        "flags": flags,
                    }
                    cursor.execute(
                        """
                        INSERT INTO flows(
                            uuid,
                            raw,
                            agent_address,
                            src_ip,
                            dst_ip,
                            proto,
                            src_port,
                            dst_port,
                            tos,
                            bytes,
                            packets,
                            start_time,
                            end_time,
                            flags,
                            ifname
                            )
                        VALUES (
                            :uuid,
                            :raw,
                            :agent_address,
                            :src_ip,
                            :dst_ip,
                            :proto,
                            :src_port,
                            :dst_port,
                            :tos,
                            :bytes,
                            :packets,
                            :start_time,
                            :end_time,
                            :flags,
                            :ifname
                            )
                        """,
                        data
                    )
                    self.messages.put(("DEBUG", f"{self.name}: Inserted {flow_uuid} - {str(flow)} into flows..."))
            except KeyError as e:
                self.messages.put(("WARNING", f"{self.name}: Malformed flow record: {e}..."))
            except Exception as e:
                self.messages.put(("WARNING", f"{self.name}: Sqlite exception: {e}..."))
