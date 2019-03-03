# -*- coding: utf-8 -*-

import queue
import sqlite3
import threading
import time
import uuid

import arrow
import influxdb
import math


class Writer(threading.Thread):
    worker_group = "writer"
    worker_number = 0

    def __init__(self, entries, messages, dbname, influx_params):
        super().__init__()
        Writer.worker_number += 1
        self.name = f"{self.worker_group}_{format(self.worker_number, '0>3')}"
        self.entries = entries
        self.messages = messages
        self.dbname = dbname
        self.influx_user = influx_params.get("influx_user")
        self.influx_password = influx_params.get("influx_password")
        self.influx_host = influx_params.get("influx_host")
        self.influx_port = influx_params.get("influx_user")
        self.influx_dbname = influx_params.get("influx_user")
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
                # SQLite processing
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
                    # Flow recording
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
                    # Timeseries recording
                    start_second = math.floor(start_time)
                    end_second = math.ceil(end_time)
                    duration = end_second - start_second
                    if duration <= 1:
                        # Only one record
                        data = {
                            "seconds": start_second,
                            "uuid": flow_uuid,
                            "agent_address": agent_address,
                            "ifname": ifname,
                            "src_ip": src_ip,
                            "dst_ip": dst_ip,
                            "proto": proto,
                            "src_port": src_port,
                            "dst_port": dst_port,
                            "bytes": length,
                            "packets": packets,
                            "flows": 1,
                        }
                        cursor.execute(
                            """
                            INSERT INTO timeseries (
                                seconds,
                                uuid,
                                agent_address,
                                ifname,
                                src_ip,
                                dst_ip,
                                proto,
                                src_port,
                                dst_port,
                                bytes,
                                packets,
                                flows
                                )
                            VALUES (
                                :seconds,
                                :uuid,
                                :agent_address,
                                :ifname,
                                :src_ip,
                                :dst_ip,
                                :proto,
                                :src_port,
                                :dst_port,
                                :bytes,
                                :packets,
                                :flows
                                )
                            """,
                            data
                        )
                        self.messages.put(("DEBUG", f"{self.name}: Inserted one record into timeseries..."))
                    else:
                        # Mutliple records
                        for i in range(duration):
                            data = {
                                "seconds": start_second + i,
                                "uuid": flow_uuid,
                                "agent_address": agent_address,
                                "ifname": ifname,
                                "src_ip": src_ip,
                                "dst_ip": dst_ip,
                                "proto": proto,
                                "src_port": src_port,
                                "dst_port": dst_port,
                                "bytes": length / duration,
                                "packets": packets / duration,
                                "flows": 1,
                            }
                            cursor.execute(
                                """
                                INSERT INTO timeseries (
                                    seconds,
                                    uuid,
                                    agent_address,
                                    ifname,
                                    src_ip,
                                    dst_ip,
                                    proto,
                                    src_port,
                                    dst_port,
                                    bytes,
                                    packets,
                                    flows
                                    )
                                VALUES (
                                    :seconds,
                                    :uuid,
                                    :agent_address,
                                    :ifname,
                                    :src_ip,
                                    :dst_ip,
                                    :proto,
                                    :src_port,
                                    :dst_port,
                                    :bytes,
                                    :packets,
                                    :flows
                                    )
                                """,
                                data
                            )
                        self.messages.put(("DEBUG", f"{self.name}: Inserted {duration - 1} records into timeseries..."))
                # InfluxDB processing
                influx_user = self.influx_user
                infux_password = self.influx_password
                influx_host = self.influx_host
                influx_port = self.influx_port
                influx_dbname = self.influx_dbname
                json_body = []
                client = influxdb.InfluxDBClient(influx_host, influx_port, influx_user, infux_password, influx_dbname)
                if duration <= 1:
                    json_body.extend([
                        {
                            "measurement": "activities",
                            "tags": {
                                "agent": agent_address,
                                "ifname": ifname,
                                "src_ip": src_ip,
                                "dst_ip": dst_ip,
                                "proto": proto,
                                "src_port": src_port,
                                "dst_port": dst_port,
                            },
                            "fields": {
                                "bytes": float(length),
                                "packets": float(packets),
                                "flows": 1.,
                            },
                            "time": arrow.get(start_second).format('YYYY-MM-DD HH:mm:ss ZZ')
                        }
                    ])
                else:
                    for i in range(duration):
                        json_body.extend([
                            {
                                "measurement": "activities",
                                "tags": {
                                    "agent": agent_address,
                                    "ifname": ifname,
                                    "src_ip": src_ip,
                                    "dst_ip": dst_ip,
                                    "proto": proto,
                                    "src_port": src_port,
                                    "dst_port": dst_port,
                                },
                                "fields": {
                                    "bytes": float(length / duration),
                                    "packets": float(packets / duration),
                                    "flows": 1.,
                                },
                                "time": arrow.get(start_second + i).format('YYYY-MM-DD HH:mm:ss ZZ'),
                            }
                        ])
                if client.write_points(json_body):
                    self.messages.put(("DEBUG", f"{self.name}: Inserted {json_body} into InfluxDB..."))
                else:
                    self.messages.put(("WARNING", f"{self.name}: Couldn't write into InfluxDB..."))
            except KeyError as e:
                self.messages.put(("WARNING", f"{self.name}: Malformed flow record: {e}..."))
            except Exception as e:
                self.messages.put(("WARNING", f"{self.name}: Exception raised: {e}..."))
