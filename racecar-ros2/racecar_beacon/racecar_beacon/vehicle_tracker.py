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

def main():
    #Créer socket UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Vehicle tracker started")
    try:
        #Associer adresse et port au socket
        s.bind((HOST, PORT))
        while True:
            print("waiting for data")
            #On attend pour 16 octets, ignorer adresse
            data, _ = s.recvfrom(16)
            print("data recieved")
            #Pas de données
            if not data:
               print("no data")
               break
            #unmarshalize dans l'ordre packed par le sender. float, float, float, int. ! pour big endian
            x, y, theta, ip_int = unpack('!fffi', data)
            
            #Mettre sur terminal dans l'ordre demandé
            print(f"x: {x:.3f}, y: {y:.3f}, theta: {theta:.3f}, (ip: {ip_int})")
            
    #Manual Interrupt
    except KeyboardInterrupt:
        print("interrupted")
    #Fermer le socket
    finally:
        print("Leaving app...")
        s.close()

if __name__ == "__main__":
    main()