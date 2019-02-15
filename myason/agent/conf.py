# -*- coding: utf-8 -*-


import os
import socket

import ifaddr
import yaml

from myason.helpers.logging import create_logger

from cryptography.fernet import Fernet


def conf_is_ok(agent_logger_conf_fn, agent_conf_fn):
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
                'filename': "log/agent_error.log"
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
    log.info("Beginning agent configuration sanity checks...")
    #
    # Agent logger configuration sanity checks
    #
    log.info("Agent logger configuration checks...")
    #
    # Verify agent logger configuration file existance
    #
    log.info(f"Verifying agent logger configuration file ({agent_logger_conf_fn}) existance...")
    if not os.path.exists(agent_logger_conf_fn):
        log.error(f"Configuration file ({agent_logger_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Agent logger configuration file ({agent_logger_conf_fn}) exists...")
    #
    # Try to parse agent logger configuration file
    #
    log.info(f"Parsing agent logger configuration file ({agent_logger_conf_fn})...")
    try:
        with open(agent_logger_conf_fn) as conf_fn:
            agent_logger_conf = conf_fn.read()
        agent_logger_conf = yaml.load(agent_logger_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing agent logger configuration file ({agent_logger_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed agent logger configuration file ({agent_logger_conf_fn})...")
    #
    # Verify agent logger conf is a valid configuration
    #
    log.info(f"Verifying if agent logger configuration file ({agent_logger_conf_fn}) is valid...")
    try:
        create_logger("myason_agent", agent_logger_conf)
    except ValueError as e:
        log = create_logger('root', default_logging)
        log.error(f"Agent logger configuration file ({agent_logger_conf_fn}): {e}... exiting!")
        return False
    log = create_logger('root', default_logging)
    log.info(f"Agent logger configuration file ({agent_logger_conf_fn}) is valid...")
    #
    # Agent configuration sanity checks
    #
    log.info("Agent configuration checks...")
    #
    # Verify agent configuration file existance
    #
    log.info(f"Verifying agent configuration file ({agent_conf_fn}) existance...")
    if not os.path.exists(agent_conf_fn):
        log.error(f"Configuration file ({agent_conf_fn}) doesn't exits... exiting!")
        return False
    log.info(f"Agent configuration file ({agent_conf_fn}) exists...")
    #
    # Try to parse agent configuration file
    #
    log.info(f"Parsing agent configuration file ({agent_conf_fn})...")
    try:
        with open(agent_conf_fn) as conf_fn:
            agent_conf = conf_fn.read()
        agent_conf = yaml.load(agent_conf)
    except yaml.YAMLError as e:
        log.error(f"Error parsing agent configuration file ({agent_conf_fn})... exiting!")
        log.error(e)
        return False
    log.info(f"Successfully parsed agent configuration file ({agent_conf_fn})...")
    #
    # Ckeck agent configuration items
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) items...")
    #
    # Check interfaces item
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) item interfaces...")
    iflist = agent_conf.get("interfaces", None)
    if iflist is None:
        log.error(f"Missing interfaces in agent configuration file ({agent_conf_fn})... Exiting!")
        return False
    if not isinstance(iflist, list):
        log.error(f"Interfaces in agent configuration file ({agent_conf_fn}) must be a list... Exiting!")
        return False
    #
    # Check interfaces names
    #
    adapters = [ifname.nice_name for ifname in ifaddr.get_adapters()]
    for ifname in iflist:
        log.info(f"Checking agent configuration file ({agent_conf_fn}) interfaces names...")
        if ifname not in adapters:
            log.error(
                f"Interface {ifname} in agent configuration file ({agent_conf_fn}), {ifname} is not valid... Exiting!"
            )
    log.info(f"Interfaces in agent configuration file ({agent_conf_fn}) passed...")
    #
    # Ckeck socket creation
    #
    log.info(f"Checking agent configuration file ({agent_conf_fn}) socket creation...")
    collector_address = agent_conf.get("collector_address", "127.0.0.1")
    collector_port = agent_conf.get("collector_port", 9999)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(str("Test").encode(), (collector_address, collector_port))
    except OverflowError:
        log.error(
            f"Interfaces in agent configuration file ({agent_conf_fn}), collector_port={collector_port} invalid..."
        )
        return False
    except socket.gaierror:
        log.error(
            f"Interfaces in agent configuration file ({agent_conf_fn}), collector_address={collector_address} invalid..."
        )
        return False
    #
    # Check fernet key presence
    #
    key = agent_conf.get("key", None)
    if key is None:
        log.error(f"Fernet key in agent configuration file ({agent_conf_fn}), is not present...")
        return False
    #
    # Check key validity
    #
    try:
        Fernet(key.encode())
    except Exception as e:
        log.error(f"Fernet key in agent configuration file ({agent_conf_fn}), is not valid... {e}")
        return False
    #
    # Exiting sanity checks with the relevant message
    #
    log.info("Agent configuration checks passed...")
    log.info("Starting the agent...")
    return True
