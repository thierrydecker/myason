#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import logging.config
import os
import yaml


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
    # Exiting sanity checks with the relevant message
    #
    if conf_ok:
        log.info("Collector configuration checks passed...")
        log.info("Starting the collector...")
        return True
    else:
        log.error("Collector configuration checks failed... Exiting!")
        return False


def collector(logger_conf_fn, collector_conf_fn):
    if not conf_is_ok(logger_conf_fn, collector_conf_fn):
        return


def main():
    collector(
        logger_conf_fn="collector_logger.yml",
        collector_conf_fn="collector.yml"
    )


if __name__ == '__main__':
    main()
