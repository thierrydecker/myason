# Myason Project

Myason aims to become a traffic engineering tool allowing, in the long term, a fine analysis
of application flows transiting on a network of any size.

## Myason documents

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Contributions](CONTRIBUTING.md)
- [Licence](LICENCE.md)
- [Authors summary](AUTHORS.md)
- [Project history](HISTORY.md)

## Technologies

Myason developement is currently based on following technologies:

- [Python (3.7)](https://www.python.org)
- [Scapy (2.4.2)](https://scapy.net/)
- [PyYaml (3.13)](https://pyyaml.org/wiki/PyYAML)
- [ifaddr (0.1.6)](https://github.com/pydron/ifaddr)

We strongly encourage using virtual environnements in the developement process. 

# Application usage
## Myason:

    python myason.py [-h] {agent,collector,ifconfig} ...

    positional arguments:

        {agent,collector,ifconfig}
            agent           agent help
            collector       server help
            ifconfig        Prints list of available adapters
            keygen          Generates a Fernet key

    optional arguments:

        -h, --help show this help message and exit

## Myason agent:

    python myason.py agent [-h]  [-lc LOGGER_CONF] [-ac AGENT_CONF]

        optional arguments:
            -h, --help          show this help message and exit
            -lc LOGGER_CONF,    --logger-conf LOGGER_CONF
            -ac AGENT_CONF,     --agent-conf AGENT_CONF

## Myason collector:

    python myason.py collector [-h]  [-lc LOGGER_CONF] [-cc COLLECTOR_CONF]

        optional arguments:
            -h, --help          show this help message and exit
            -lc LOGGER_CONF,    --logger-conf LOGGER_CONF
            -cc COLLECTOR_CONF, --collector-conf COLLECTOR_CONF

## Myason ifconfig:

    python myason ifconfig [-h]

        optional arguments:
            -h, --help  show this help message and exit

## Myason keygen:

    python myason keygen [-h]

        optional arguments:
            -h, --help  show this help message and exit

# Application architecture

## Agent

![Agent architecture](images/myason_agent_architecture.jpg)

A stack of four threads is running for each listenned interface :

- A sniffer in charge of capturing the packets.

- A packet processor in charge of the packets dissection.

- An exporter processor in charge of sending flow entries to a collector.

- A message processor in charge of the logging stuff of previous threads.

These threads communicate to each other by the mean of three thread-safe FIFO queues:

- A packets queue filled by the sniffer and consumed by the packet processor.


- A flows entries queue filled by the packet processor and consumed by
the exporter processor.

- A messages queue filled by the sniffer, the packet and the exporter processors
and consumed by the message processor.

### Packet processor

Everything begins with the **cache** and ends with the **exporter**.

The **cache** has a couple of basic jobs to do:

- Interrogate data header of the packet and either mark it as a new flow or add it to part of an existing flow.
- Keep track of the flow timers and other factors, and when a flow is considered _**complete**_,
send it to the exporter (if one exists) and delete the flow. This process is known as flow aging.

The cache only keeps information on current and non-expired flows.

Each flow is defined as having values that match the followinf 7 fields uniquely:

- Source IP address
- Destination IP address
- Source port number
- Destination port number
- Layer 3 protocol type
- ToS byte value
- IfIndex number, also called the logical interface number

When a packet is processed and **all seven of these fileds match** an existing flow, it's not considered a
new flow but part of an existing flow. If any part of these seven fields doesn't exactly match an existing
flow, it's then a new flow and a new flow record is created.

These above fields are the **key fields**.

The following fields are **non-key fields** and are stored in the flow record identified by the **key fields**.

- Bytes
- Packets
- Output interface IfIndex
- Flow start and finish time
- Next hop IP
- Network masks
- TCP flags
- Source and destination BGP AS numbers

The **cache aging** 

The agent may have a limited amount of memory to store information, so at some point the device has to make
room for new flows. This is where flow aging and exporting comes into play.

The packet processor keeps track of of several factors regarding the flows and the status of the cache itself.

Here are the factors the agent uses to age flows and either delete them or export to a collector and
then delete. These are listed in order of precedence:

- Cache maximum size (max number of flow records).
- A TCP connection has been terminated by a RST (reset) or FIN (finish) flag in the flow.
- An active flow timer or inactive flow timer limit is reached.

### Exporter processor

The exporter processor sends the aged flow entries to the collector which is in
charge of storing them.

The entries are marshalled to a json string, base 64 encoded and then sent to the
collector.

## Collector

![Collector architecture](images/myason_collector_architecture.jpg)


Three thread type are running:

- A Listener

- A (configurable number of) processor

- A (configurable number of) writer

- A messenger

## Payloads encryption

# Fernet Spec

This [document](https://github.com/fernet/spec/blob/master/Spec.md) describes version 0x80
(currently the only version) of the fernet format.

Conceptually, fernet takes a user-provided *message* (an arbitrary
sequence of bytes), a *key* (256 bits), and the current
time, and produces a *token*, which contains the message in a form
that can't be read or altered without the key.

To facilitate convenient interoperability, this spec defines the
external format of both tokens and keys.

All encryption in this version is done with AES 128 in CBC mode.

All base 64 encoding is done with the "URL and Filename Safe"
variant, defined in [RFC 4648](http://tools.ietf.org/html/rfc4648#section-5) as "base64url".

## Key Format

A fernet *key* is the base64url encoding of the following
fields:

    Signing-key ‖ Encryption-key

- *Signing-key*, 128 bits
- *Encryption-key*, 128 bits

## Token Format

A fernet *token* is the base64url encoding of the
concatenation of the following fields:

    Version ‖ Timestamp ‖ IV ‖ Ciphertext ‖ HMAC

- *Version*, 8 bits
- *Timestamp*, 64 bits
- *IV*, 128 bits
- *Ciphertext*, variable length, multiple of 128 bits
- *HMAC*, 256 bits

Fernet tokens are not self-delimiting. It is assumed that the
transport will provide a means of finding the length of each
complete fernet token.

## Token Fields

### Version

This field denotes which version of the format is being used by
the token. Currently there is only one version defined, with the
value 128 (0x80).

### Timestamp

This field is a 64-bit unsigned big-endian integer. It records the
number of seconds elapsed between January 1, 1970 UTC and the time
the token was created.

### IV

The 128-bit Initialization Vector used in AES encryption and
decryption of the Ciphertext.

When generating new fernet tokens, the IV must be chosen uniquely
for every token. With a high-quality source of entropy, random
selection will do this with high probability.

### Ciphertext

This field has variable size, but is always a multiple of 128
bits, the AES block size. It contains the original input message,
padded and encrypted.

### HMAC

This field is the 256-bit SHA256 HMAC, under signing-key, of the
concatenation of the following fields:

    Version ‖ Timestamp ‖ IV ‖ Ciphertext

Note that the HMAC input is the entire rest of the token verbatim,
and that this input is *not* base64url encoded.

## Generating

Given a key and message, generate a fernet token with the
following steps, in order:

1. Record the current time for the timestamp field.
2. Choose a unique IV.
3. Construct the ciphertext:
   1. Pad the message to a multiple of 16 bytes (128 bits) per [RFC
   5652, section 6.3](http://tools.ietf.org/html/rfc5652#section-6.3).
   This is the same padding technique used in [PKCS #7
   v1.5](http://tools.ietf.org/html/rfc2315#section-10.3) and all
   versions of SSL/TLS (cf. [RFC 5246, section
   6.2.3.2](http://tools.ietf.org/html/rfc5246#section-6.2.3.2) for
   TLS 1.2).
   2. Encrypt the padded message using AES 128 in CBC mode with
   the chosen IV and user-supplied encryption-key.
4. Compute the HMAC field as described above using the
user-supplied signing-key.
5. Concatenate all fields together in the format above.
6. base64url encode the entire token.

## Verifying

Given a key and token, to verify that the token is valid and
recover the original message, perform the following steps, in
order:

1. base64url decode the token.
2. Ensure the first byte of the token is 0x80.
3. If the user has specified a maximum age (or "time-to-live") for
the token, ensure the recorded timestamp is not too far in the
past.
4. Recompute the HMAC from the other fields and the user-supplied
signing-key.
5. Ensure the recomputed HMAC matches the HMAC field stored in the
token, using a constant-time comparison function.
6. Decrypt the ciphertext field using AES 128 in CBC mode with the
recorded IV and user-supplied encryption-key.
7. Unpad the decrypted plaintext, yielding the original message.

Code is automatically reviewed with 
[![CodeFactor](https://www.codefactor.io/repository/github/thierrydecker/myason/badge)](https://www.codefactor.io/repository/github/thierrydecker/myason)