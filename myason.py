#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import agent
import collector
from myason.ifconfig import adapters
from myason.crypto import keygen


def main():
    # Create the top-level parser
    parser = argparse.ArgumentParser(prog="myason")
    subparsers = parser.add_subparsers(help="", dest="app")
    subparsers.required = True
    # Create the parser for "agent" command
    parser_agent = subparsers.add_parser(name="agent", help="agent help")
    parser_agent.add_argument("-lc", "--agent-logger-conf", default="config/agent_logger.yml")
    parser_agent.add_argument("-ac", "--agent-conf", default="config/agent.yml")
    # Create the parser for "collector" command
    parser_collector = subparsers.add_parser(name="collector", help="collector help")
    parser_collector.add_argument("-lc", "--collector-logger-conf", default="config/collector_logger.yml")
    parser_collector.add_argument("-cc", "--collector-conf", default="config/collector.yml")
    # Create the parser for ifconfig
    parser_ifconfig = subparsers.add_parser(name="ifconfig", help="Prints list of available adapters")
    # Create the parser for keygen
    parser_keygen = subparsers.add_parser(name="keygen", help="Generates a Fernet key")
    # Parse arguments
    arguments = parser.parse_args()
    if arguments.app == "agent":
        # Start agent
        agent.agent(
            agent_conf_fn=arguments.agent_conf,
            logger_conf_fn=arguments.agent_logger_conf,
        )
    elif arguments.app == "collector":
        # Start collector
        collector.collector(
            collector_conf_fn=arguments.collector_conf,
            logger_conf_fn=arguments.collector_logger_conf,
        )
    elif arguments.app == "ifconfig":
        # Starts ifconfig
        adapters.get_adapters()
    elif arguments.app == "keygen":
        # Starts keygen
        keygen.get_key()


if __name__ == '__main__':
    main()
