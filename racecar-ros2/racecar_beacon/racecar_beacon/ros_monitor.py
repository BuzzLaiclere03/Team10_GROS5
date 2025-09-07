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
        
        self.get_logger().info("hello")

        # État du robot
        self.id = int(0xFFFF)
        self.position = tuple([float(0), float(0), float(0)])
        self.obstacle_detected = bool(False)

        # Paramètres du Socket
        self.host = self.declare_parameter("host", "10.0.0.42").value
        self.remote_request_port = self.declare_parameter(
            "remote_request_port", 65432
        ).value
        
        #Paramètres du Socket pour diffusion
        self.broadcast = self.declare_parameter("broadcast", "10.0.0.255").value
        self.position_broad_port = self.declare_parameter(
            "pos_broadcast_port", 65431
        ).value

        #Créer Socket TCP et associer adresse et port
        self.socket_TCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_TCP.bind((self.host, self.remote_request_port))

        #Créer un thread pour la méthode remote_request_loop
        self.remote_request_t = threading.Thread(target=self.remote_request_loop)

        #Créer socket UDP
        self.udpsock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) 
        #Activer diffusion
        self.udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
        #Reutiliser addr/port au cas où la connexion ferme et reouvre
        self.udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)

        #Inscription aux topics ROS
        self.subscription = self.create_subscription(Odometry, "odometry/filtered", self.odom_callback, 1)
        self.sub_laser = self.create_subscription(LaserScan, "/scan", self.odom_callback, 1)

        #Commencer le thread
        self.remote_request_t.start()
        
        #Rouler le code à chaque seconde (1 Hz)
        self.create_timer(1.0, self.send_position_broadcast)

        self.get_logger().info(f"{self.get_name()} started.")

    def remote_request_loop(self):
        #Écouter pour une connexion (1 seule)
        self.socket_TCP.listen(1)

        #Attendre et initier la communication avec Addr/Port
        conn, addr = self.socket_TCP.accept()

        self.get_logger().info(f"Client connected: {addr}")

        #Seulement client peut fermer la connexion
        while rclpy.ok():
            #Rx des données
            RXdata = conn.recv(1024)
            #Unmarshaling des données, on attend 4 octets string big endian
            requested_code = unpack("!4s", RXdata)[0].decode('ascii')
            self.get_logger().info(f"requested_code: {requested_code}")
            
            #ID
            if requested_code == "RBID":
                #on attend 4 octets integer et 12 octets padding
                self.TXdata = pack("!i12x", self.id)
                conn.send(self.TXdata)

            #Position
            elif requested_code == "RPOS":
                #on attend 3 floats et 4 octets padding
                self.TXdata = pack("!fff4x", self.position[0], self.position[1], self.position[2])
                conn.send(self.TXdata)

            #obstacle
            elif requested_code == "OBSF":
                #on attend un integer et 12 octets padding
                self.TXdata = pack("!i12x",int(self.obstacle_detected))
                conn.send(self.TXdata)

            #Aucun des options
            else:
                self.get_logger().info("data unavailable")
        
    #Diffusion a vehicule tracker
    def send_position_broadcast(self):
        #Marshaling des données, 4 floats et 1 integer avec Big Endian
        data = pack('!fffi', self.position[0], self.position[1], self.position[2], self.id)
        
        self.get_logger().info("UDP target IP: %s" % self.broadcast)
        #Envoyer
        self.udpsock.sendto(data, (self.broadcast, self.position_broad_port))

    #Fermer le thread
    def shutdown(self):
        """Gracefully shutdown the threads BEFORE terminating the node."""
        self.remote_request_t.join()

    #Calcul odométrie
    def odom_callback(self, msg: Odometry):
        #Isoler la position x,y et orientation yaw selon données quaternions
        self.position = (
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            yaw_from_quaternion(msg.pose.pose.orientation)
        )

    #Logique Obstacle et Lidar
    def lidar_callback(self, msg: LaserScan):
        #remettre la valeur à faux
        self.obstacle_detected = False
        ranges = msg.ranges
        self.get_logger().info(f"lidar: {ranges}")
        #Itérer sur les données
        for range_value in ranges:
            #Vérifier pour une valeur inférieur à 1 mètres
            if range_value < 1.0:
                #Obstacle détecté
                self.obstacle_detected = True
                print(self.obstacle_detected)
                break


def main(args=None):
    try:
        #initialisation des nodes
        rclpy.init(args=args)
        node = ROSMonitor()
        rclpy.get_default_context().on_shutdown(node.shutdown)
        #Node event loop
        rclpy.spin(node)
        
    #Manual interrupt
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    #Fermer et libérer les resources ROS
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
