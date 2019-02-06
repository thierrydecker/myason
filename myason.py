#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import agent
import collector


def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog="myason")
    subparsers = parser.add_subparsers(help="either agent or collector instance", dest="app")
    subparsers.required = True
    # create the parser for "agent" command
    parser_agent = subparsers.add_parser(name="agent", help="agent help")
    parser_agent.add_argument("-lc", "--agent-logger-conf", default="agent_logger.yml")
    parser_agent.add_argument("-ac", "--agent-conf", default="agent.yml")
    # create the parser for "collector" command
    parser_collector = subparsers.add_parser(name="collector", help="server help")
    # parse arguments
    arguments = parser.parse_args()
    if arguments.app == "agent":
        # Start agent
        agent.agent(
            agent_conf_fn=arguments.agent_conf,
            logger_conf_fn=arguments.agent_logger_conf
        )
    else:
        # start collector
        # collector.collector()
        pass


if __name__ == '__main__':
    main()
