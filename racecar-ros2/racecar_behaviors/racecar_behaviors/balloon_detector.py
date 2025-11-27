#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point, PoseStamped
import numpy as np
import datetime
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import tf2_ros


class BalloonDetector(Node):

    def __init__(self):
        super().__init__('balloon_detection')

        self.balloons = []
        self.bridge = CvBridge()
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.take_picture = 0
        self.distance = None
        self.angle = None
        self.balloon_map_pos_x = 0.0
        self.balloon_map_pos_y = 0.0

        self.balloon_dst_from_car = self.create_subscription(Point,'/balloon_dst_from_car',self.balloon_position_callback,1)
        self.map_update_timer = self.create_timer(0.1, self.update_balloon_map_position) 
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 1)
        self.sub = self.create_subscription(Image, '/racecar/camera', self.image_callback, 1)

        self.center_timer = 0
        self.center_end_time = None

    def balloon_position_callback(self, msg):
        self.distance = msg.x
        self.angle = msg.y
        z = msg.z

        # If sleep for 5 seconds, set speed and angle to 0
        if getattr(self, 'waiting', False):
            twist = Twist()
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_vel_pub.publish(twist)
            return

        if len(self.balloons) > 1: 
            for (x, y) in self.balloons:
                if np.sqrt((x - self.balloon_map_pos_x)**2 + (y - self.balloon_map_pos_y)**2) < 2.0:
                    self.get_logger().info(f"OLD BALLOON")
                    return
                else:
                    continue

        if z != -1.0:
            return

        self.get_logger().info(f"New Balloon ({self.distance:.2f}, {self.angle:.2f})")
        twist = Twist()
        twist.linear.x = 0.2

        if self.angle < -0.1:
            twist.angular.z = -0.1
            self.get_logger().info(f"In first condition")
            self.cmd_vel_pub.publish(twist)
            return
        if self.angle > 0.1:
            twist.angular.z = 0.1
            self.get_logger().info(f"In second condition")
            self.cmd_vel_pub.publish(twist)
            return
        if self.distance > 2.0:
            self.get_logger().info("Too far to save, keep moving forward")
            twist.linear.x = 0.2
            self.cmd_vel_pub.publish(twist)
            return

        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)

        self.waiting = True       
        self.get_logger().info(f"passed conditions")     
        self.wait_after_picture()

    def wait_after_picture(self):
        if self.center_timer == 0:   
            self.center_end_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
            self.get_logger().info(f"center end time {self.center_end_time}")
            twist = Twist()
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_vel_pub.publish(twist)
            self.center_timer = self.create_timer(0.05, self.center_timer_callback)

    def center_timer_callback(self):
        if datetime.datetime.now() >= self.center_end_time:
            self.center_end_time = None
            self.get_logger().info("centered")
            self.destroy_timer(self.center_timer)
            if self.take_picture == 0:
                self.take_picture = 1   
            self.nouveau_ballon()
            self.center_timer = 0 
            self.waiting = False    
            self.get_logger().info(f"5 seconds passed")
        
    def nouveau_ballon(self):
        self.balloons.append((self.balloon_map_pos_x, self.balloon_map_pos_y))
        self.get_logger().info(f"New Balloon ({self.balloon_map_pos_x:.2f}, {self.balloon_map_pos_y:.2f})")

    def image_callback(self, msg):
        if len(self.balloons) > 1: 
            for (x, y) in self.balloons:
                if np.sqrt((x - self.balloon_map_pos_x)**2 + (y - self.balloon_map_pos_y)**2) < 2.0:
                    self.get_logger().info(f"OLD BALLOON")
                    return
                else:
                    continue
        if self.take_picture == 1:
            self.get_logger().info(f'SAVING IMAGE -------------------------------------------------------------------------------------')
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'rgb8')
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f'balloon_from_time_{timestamp}.jpg'

            cv2.imwrite(filename, cv_image)
            self.get_logger().info(f'Saved {filename}')
            self.take_picture = 0 

    def update_balloon_map_position(self):
            if self.distance is None or self.angle is None:
                return  

            try:
                trans = self.tf_buffer.lookup_transform(
                    'racecar/map',         
                    'racecar/base_link',    
                    rclpy.time.Time()
                )
                robot_x_in_map = trans.transform.translation.x
                robot_y_in_map = trans.transform.translation.y
                q = trans.transform.rotation
                siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
                cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
                robot_yaw = np.arctan2(siny_cosp, cosy_cosp)
            except Exception as e:
                self.get_logger().warn(f'TF lookup failed: {e}')
                return

            total_angle = robot_yaw + self.angle
            self.balloon_map_pos_x = robot_x_in_map + self.distance * np.cos(total_angle)
            self.balloon_map_pos_y = robot_y_in_map + self.distance * np.sin(total_angle)

            self.get_logger().info(f"Balloon in map: x={self.balloon_map_pos_x:.2f}, y={self.balloon_map_pos_y:.2f}")
 


def main(args=None):
    rclpy.init(args=args)
    node = BalloonDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
