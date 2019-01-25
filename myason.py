#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import agent
import server


def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog='myason')
    subparsers = parser.add_subparsers(help='either agent or server instance', dest='app')
    subparsers.required = True
    # create the parser for "agent" command
    parser_agent = subparsers.add_parser(name='agent', help='agent help')
    # create the parser for "server" command
    parser_server = subparsers.add_parser(name='server', help='server help')
    # parse arguments
    arguments = parser.parse_args()
    # start the agent or the server
    if arguments.app == 'agent':
        agent.agent()
    else:
        server.server()


if __name__ == '__main__':
    main()
