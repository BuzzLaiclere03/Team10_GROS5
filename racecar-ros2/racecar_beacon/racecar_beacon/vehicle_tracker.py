#!/usr/bin/env python3

import socket
from struct import unpack

"""
NOTES:

- This process MUST listen to a different port than the RemoteRequest client;
- A socket MUST be closed BEFORE exiting the process.
"""

HOST = str("10.0.0.255")
PORT = int(65431)

#sudo tcpdump -i any udp and dst host 10.0.0.255 and dst port 654321

def main():
    #socket, Internet et UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Vehicle tracker started")
    try:
        #connexion au port
        s.bind((HOST, PORT))
        while True:
            #je veux 16 bytes
            print("waiting for data")
            data, addr = s.recvfrom(16)
            print("data recieved")
            if not data:
               print("moi quand ta mere etre comme")
               break
            #unpack dans l'ordre packed par le sender. float, float, float, int. ! pour big endian
            x, y, theta, ip_int = unpack('!fffi', data)
            print(f"x: {x:.3f}, y: {y:.3f}, theta: {theta:.3f}, (ip: {ip_int})")
    except KeyboardInterrupt:
        print("interrupted")
    finally:
        print("Leaving app...")
        s.close()

#def main():
    # TODO: Implement the PositionBroadcast client here.
#    pass


if __name__ == "__main__":
    main()
