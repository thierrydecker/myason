#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import agent
import collector


def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog='myason')
    subparsers = parser.add_subparsers(help='either agent or collector instance', dest='app')
    subparsers.required = True
    # create the parser for "agent" command
    parser_agent = subparsers.add_parser(name='agent', help='agent help')
    parser_agent.add_argument("-lc", "--logger-conf")
    parser_agent.add_argument("-ac", "--agent-conf")
    # create the parser for "server" command
    parser_server = subparsers.add_parser(name='collector', help='server help')
    # parse arguments
    arguments = parser.parse_args()
    # start the agent or the server
    if arguments.app == 'agent':
        agent.agent()
    else:
        collector.collector()


if __name__ == '__main__':
    main()
