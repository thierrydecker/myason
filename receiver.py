import socket
import select

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(("192.168.1.53", 9999))

    while True:
        rlist, wlist, elist = select.select([sock], [], [], 1)
        if not rlist:
            pass
        else:
            for sock in rlist:
                data, ip = sock.recvfrom(1024)
                print(f"Received {data} from {ip}")

except OSError as e:
    print(e)
