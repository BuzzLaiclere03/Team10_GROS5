#!/usr/bin/env python3
import socket
from struct import unpack, pack
from enum import Enum

"""
NOTES:

- This process MUST listen to a different port than the PositionBroadcast client;
- A socket MUST be closed BEFORE exiting the process.
"""

HOST = "10.0.0.42"
PORT = 65432 

class VehicleData(Enum):
    ID = "RBID"
    POSITION = "RPOS"
    OBSTACLE_DETECTED = "OBSF"

def remote_request(socket: socket):
    while True:
        print(f"Enter : \nFor ID: {VehicleData.ID.value}\nFor Position: {VehicleData.POSITION.value}\nFor Obstacle detected: {VehicleData.OBSTACLE_DETECTED.value}")
        try:
            input_data = input().strip()
            if input_data not in [v.value for v in VehicleData]:
                print("Not a choice, Enter : \nFor ID: 1\nFor Position: 2\nFor Obstacle detected: 3")
                continue
            print(f"Sending input {input_data} to the server")
            socket.send(pack('!4s', input_data.encode("ascii")))

            if input_data == VehicleData.ID.value:  
                data = socket.recv(16)
                #print(f"Recieved data: {data}")
                #print(f"Received hex: {data.hex()}")  # shows 00000002
                vehicle_id = unpack('!i12x', data)[0]
                print(f"\nID: {vehicle_id}\n")


            elif input_data == VehicleData.POSITION.value:  
                data = socket.recv(16)
                #print(f"Recieved data: {data}")
                #print(f"Received hex: {data.hex()}")  # shows 00000002
                pos_x, pos_y, pos_yaw = unpack('!fff4x', data)
                print(f"\nPosition: x={pos_x:.3f}, y={pos_y:.3f}, yaw={pos_yaw:.3f}\n")


            elif input_data == VehicleData.OBSTACLE_DETECTED.value:
                data = socket.recv(16)
                #print(f"Recieved data: {data}")
                #print(f"Received hex: {data.hex()}")  # shows 00000002
                obstacle_detected = unpack('!i12x', data)[0]
                print(f"\nObstacle detected: {obstacle_detected}\n")
        except(UnboundLocalError, ValueError):
            print("Not a choice, Enter : \nFor ID: 1\nFor Position: 2\nFor Obstacle detected: 3")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"remote_client is starting. \nConnecting to the beacon server at {HOST}")
    try:
        s.connect((HOST, PORT))
        remote_request(s)
    except(ConnectionRefusedError):
        print(f"Unable to connect to {HOST}. Connection refused")
    except(ConnectionError):
        print(f"Unable to connect to {HOST}. Connection error")
    finally:
        print("Ended")
    s.close()


if __name__ == "__main__":
    main()