# Myason Project

Myason aims to become a traffic engineering tool allowing, in the long term, a fine analysis
of application flows transiting on a network of any size.

## Myason documents

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Contributions](CONTRIBUTING.md)
- [Licence](LICENCE.md)
- [Authors summary](AUTHORS.md)
- [Project history](HISTORY.md)


## Application usage:

    python myason.py [-h] {agent, server} ...

    positional arguments:

        {agent,server}  either agent or server instance
            agent           agent help
            server          server help

    optional arguments:

        -h, --help show this help message and exit

## Application architecture:

### Agent:

Three threads are running:

- A sniffer in charge of capturing the packets.

- A packet processor in charge of the packets dissection.

- A message processor in charge of the logging stuff.

Two FIFO queues are managed:

- A packets queue filled by the sniffer and consumed by the packet processor.

- A messages queue filled by the sniffer and the packet processor and consumed 
by the message processor.

Code is automatically reviewed with 
[![CodeFactor](https://www.codefactor.io/repository/github/thierrydecker/myason/badge)](https://www.codefactor.io/repository/github/thierrydecker/myason)