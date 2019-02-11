# -*- coding: utf-8 -*-


import yaml


def collector_conf_loader(collector_conf_fn):
    with open(collector_conf_fn) as conf_fn:
        collector_conf = conf_fn.read()
    collector_conf = yaml.load(collector_conf)
    return collector_conf


def agent_conf_loader(agent_conf_fn):
    with open(agent_conf_fn) as conf_fn:
        agent_conf = conf_fn.read()
    agent_conf = yaml.load(agent_conf)
    return agent_conf


def conf_loader(conf_fn):
    with open(conf_fn) as conf_fn:
        conf = conf_fn.read()
    conf = yaml.load(conf)
    return conf
