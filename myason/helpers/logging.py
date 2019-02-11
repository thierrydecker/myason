# -*- coding: utf-8 -*-


import logging
import logging.config

import yaml


def create_logger(name, configuration):
    logging.config.dictConfig(configuration)
    return logging.getLogger(name)


def logger_conf_loader(logger_conf_fn):
    with open(logger_conf_fn) as conf_fn:
        logger_conf = conf_fn.read()
    logger_conf = yaml.load(logger_conf)
    return logger_conf
