#!/usr/bin/env python
# -*- coding: utf-8 -*-


from cryptography.fernet import Fernet


def get_key():
    key = Fernet.generate_key().decode()
    print(f"Generated key: {key}")
    print("Keep your secret, secret!")


def main():
    get_key()


if __name__ == "__main__":
    main()
