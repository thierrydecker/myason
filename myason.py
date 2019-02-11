#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

from myason.agent import agent
from myason.collector import collector
from myason.ifconfig import adapters


def main():
    # Create the top-level parser
    parser = argparse.ArgumentParser(prog="myason")
    subparsers = parser.add_subparsers(help="", dest="app")
    subparsers.required = True
    # Create the parser for "agent" command
    parser_agent = subparsers.add_parser(name="agent", help="agent help")
    parser_agent.add_argument("-lc", "--agent-logger-conf", default="agent_logger.yml")
    parser_agent.add_argument("-ac", "--agent-conf", default="agent.yml")
    # Create the parser for "collector" command
    parser_collector = subparsers.add_parser(name="collector", help="collector help")
    # Create the parser
    parser_ifconfig = subparsers.add_parser(name="ifconfig", help="Prints list of available adapters")
    # Parse arguments
    arguments = parser.parse_args()
    if arguments.app == "agent":
        # Start agent
        agent.agent(
            agent_conf_fn=arguments.agent_conf,
            logger_conf_fn=arguments.agent_logger_conf
        )
    elif arguments.app == "collector":
        # Start collector
        collector.collector()
    else:
        # Starts ifconfig
        adapters.ifconfig()


if __name__ == '__main__':
    main()
