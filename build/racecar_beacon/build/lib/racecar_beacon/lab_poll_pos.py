#!/usr/bin/env python3

import math
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf_transformations import euler_from_quaternion

from nav_msgs.msg import Odometry


def yaw_from_quaternion(q):   # q is a list [x,y,z,w]
    _, _, yaw = euler_from_quaternion(q)
    return yaw


class PositionPoller(Node):
    def __init__(self):
        super().__init__("position_poller")
        self.subscription = self.create_subscription(
            Odometry, "/odometry/filtered", self.odometry_callback, 1
        )
        self.get_logger().info(f"{self.get_name()} started.")

    def odometry_callback(self, msg: Odometry):
        o = msg.pose.pose.orientation
        q = [o.x, o.y, o.z, o.w]

        yaw = yaw_from_quaternion(q)

        pos = msg.pose.pose.position
        self.get_logger().info(f"Position: ({pos.x:.2f}, {pos.y:.2f})")
        self.get_logger().info(f"Yaw: {math.degrees(yaw):.2f}°")



def main(args=None):
    try:
        rclpy.init(args=args)
        node = PositionPoller()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        rclpy.shutdown()
