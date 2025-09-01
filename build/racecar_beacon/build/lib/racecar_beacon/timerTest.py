#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class TimerProbe(Node):
    def __init__(self):
        super().__init__('timer_probe')
        self.count = 0
        self.timer = self.create_timer(1.0, self.tick)  # keep a handle
        self.get_logger().info("TimerProbe started")

    def tick(self):
        self.count += 1
        self.get_logger().info(f"tick {self.count}")  # use logger, not print

def main():
    rclpy.init()
    node = TimerProbe()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
