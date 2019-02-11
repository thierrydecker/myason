# -*- coding: utf-8 -*-


import os

import yaml

from myason.helpers.logging import create_logger


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
                'filename': "log/collector_error.log"
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
