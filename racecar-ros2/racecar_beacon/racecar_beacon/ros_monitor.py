#!/usr/bin/env python3

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

import socket
import threading
from struct import pack, unpack

from racecar_beacon.utils import yaw_from_quaternion


class ROSMonitor(Node):
    def __init__(self):
        super().__init__("ros_monitor")

        # Robot state
        self.id = int(0xFFFF)
        self.position = tuple([float(0), float(0), float(0)])
        self.obstacle_detected = bool(False)

        # Socket parameters
        self.host = self.declare_parameter("host", "127.0.0.1").value
        self.remote_request_port = self.declare_parameter(
            "remote_request_port", 65432
        ).value
        self.broadcast = self.declare_parameter("broadcast", "127.0.0.255").value
        self.position_broad_port = self.declare_parameter(
            "pos_broadcast_port", 65431
        ).value

        #these might have to go into the callback
        self.socket_TCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_TCP.bind((self.host, self.remote_request_port))
    
        self.remote_request_t = threading.Thread(target=self.remote_request_loop)

        # TODO: Add your subscription(s) here.
        self.subscription = self.create_subscription(Odometry, "odometry/filtered", self.odom_callback, 1)

        self.remote_request_t.start()
        self.create_timer(1.0, self.send_position_broadcast)  # 1 Hz, no drift
        self.get_logger().info(f"{self.get_name()} started.")

    def remote_request_loop(self):

        #listen for connection (1 connection)
        self.socket_TCP.listen(1)

        #wait for connection from host and port, then initiate the conn
        conn, addr = self.socket_TCP.accept()

        self.get_logger().info(f"Client connected: {addr}")

        #only client can close the connection
        while True:
            #starting to get data
            RXdata = conn.recv(1024)
            #this over here is for the first unpack. (Line 29 of remote_client)
            requested_code = unpack("!i", RXdata)[0]

            if requested_code == 1:
                self.TXdata = self.id
                conn.send(pack("!i", TXdata))

            elif requested_code == 2:
                self.TXdata = self.position
                conn.send(pack("!fff", TXdata))

            elif requested_code == 3:
                TXdata = self.obstacle_detected
                conn.send(pack("!?", TXdata))

            else:
                self.get_logger.info("data unavailable")
        


        # NOTE: It is recommended to initialize your socket here.

        # TODO: Implement the RemoteRequest service here.
        while rclpy.ok():
            pass

    # TODO: Implement the PositionBroadcast service here.
    # NOTE: It is recommended to initializae your socket locally.
    def send_position_broadcast(self):
            data = pack('!fffi', self.position[0], self.position[1], self.position[2], self.id)
            print("UDP target IP: %s" % self.host)
            print("UDP target port: %s" % self.position_broad_port)
            print("message: %s" % data)
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) # UDP
            sock.sendto(data, (self.host, self.position_broad_port))



    def shutdown(self):
        """Gracefully shutdown the threads BEFORE terminating the node."""
        self.remote_request_t.join()

    def odom_callback(self, msg: Odometry):
        self.position = (
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            yaw_from_quaternion(msg.pose.pose.orientation)
        )
        self.get_logger().info(f"Position updated: {self.position}")




def main(args=None):
    try:
        rclpy.init(args=args)
        node = ROSMonitor()
        rclpy.get_default_context().on_shutdown(node.shutdown())
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
