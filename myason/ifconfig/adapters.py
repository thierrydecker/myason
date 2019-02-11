#!/usr/bin/env python
# -*- coding: utf-8 -*-


import ifaddr


def get_adapters():
    print("\nAvailable adapters on the system:\n")
    for adapter in ifaddr.get_adapters():
        print(adapter.nice_name, )


def main():
    get_adapters()


if __name__ == "__main__":
    main()
