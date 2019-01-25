#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse


def main():
    """The entry point of the script

    This function is acting as an entry point for the script.

    Args:

    Returns:
        None

    Raises:
        None

    """

    # create the top-level parser
    parser = argparse.ArgumentParser(prog='myason')
    subparsers = parser.add_subparsers(help='either agent or server instance', dest='app')
    subparsers.required = True
    # create the parser for "agent" command
    parser_agent = subparsers.add_parser(name='agent', help='agent help')
    # create the parser for "server" command
    parser_server = subparsers.add_parser(name='server', help='server help')
    # parse arguments
    print(parser.parse_args())


if __name__ == '__main__':
    main()
