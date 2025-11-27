#!/usr/bin/env python

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from sensor_msgs.msg import LaserScan
import numpy as np
from nav_msgs.msg import Odometry
import math
import tf2_ros
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatusArray
from rclpy.action import ActionClient

class PathFollowing(Node):
    def __init__(self):
        super().__init__('path_following')
        self.angle_div = self.declare_parameter('angle_div', 8).value
        self.distance = self.declare_parameter('distance', 0.7).value
        self.distance_short = self.declare_parameter('distance_short', 0.45).value
        self.max_speed = self.declare_parameter('max_speed', 1).value
        self.max_steering = self.declare_parameter('max_steering', 0.37).value

        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 1)
        self.scan_sub = self.create_subscription(LaserScan, 'scan', self.scan_callback, 1)
        self.odom_sub = self.create_subscription(Odometry, 'odom', self.odom_callback, 1)
        self.goal_pose = self.create_publisher(PoseStamped, 'goal_pose',1)
        self._status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
            )
        self.tol = 1
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal = NavigateToPose.Goal()
        #self.prev_error = 0.0
        #self.prev_angular_cmd = 0.0
        self.goal_active = False
        self.goal_status = 0
        self.goalx = 5.0
        self.goaly = 0.0
        self.goalo = 0.0

        self.goal_flag = False
        
        
        #transformation matrix buffer shit
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        #calm down the compiler for when initX and Y are not defined
        pose = self.get_pose()
        if pose is not None:
            self.initX = pose.pose.position.x
            self.initY = pose.pose.position.y
        else:
            self.get_logger().warn("Initial pose not available yet")
            self.initX = 0.0
            self.initY = 0.0
        
        

        

        '''
        self.sub = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.get_pose,
            10
        )
        '''
        
        #goal_msg.pose = self.goal_position

        
        self.get_logger().info("testing:")
        #self.get_logger().info(self.goal_position.pose.position.x)
    #tolerances for our distances
    def toleranceMatching(self, currentX,currentY, goalX, goalY):
        return abs(currentX - goalX) <= self.tol and abs(currentY - goalY) <= self.tol
    #a function to set the goal in the right format and everything
    def manage_goal(self,goal_x, goal_y, goal_orientation):
        #proper format and stuff
        goal_msg = PoseStamped()
        goal_msg.header.frame_id = 'racecar/map'
        goal_msg.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.position.x = goal_x
        goal_msg.pose.position.y = goal_y
        goal_msg.pose.orientation.w = goal_orientation
        self.get_logger().info(f"Robot goal: x={goal_msg.pose.position.x:.3f}, y={goal_msg.pose.position.y:.3f}")
        self.goal_pose.publish(goal_msg)
        self.goal.pose = goal_msg
        # EDoesnt work without this, the action client needs to initialize
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn("Action server not ready yet")
        #this part is what puts the green on the map I believe
        #should really test without it
        self._action_client.send_goal_async(self.goal)
        
    #get the robots global pose
    def get_pose(self):
        try:
            #transformation matrix from base_link with respect to map. See lab solution
            trans = self.tf_buffer.lookup_transform(
                'racecar/map',           # target frame
                'racecar/base_link',     # source frame
                rclpy.time.Time()
            )
            pose = PoseStamped()
            #put it in the right format
            pose.header.stamp = trans.header.stamp
            pose.header.frame_id = 'racecar/base_link'
            pose.pose.position.x = trans.transform.translation.x
            pose.pose.position.y = trans.transform.translation.y
            pose.pose.position.z = trans.transform.translation.z
            pose.pose.orientation = trans.transform.rotation
            self.get_logger().info(f"Robot position: x={pose.pose.position.x:.3f}, y={pose.pose.position.y:.3f}")
            return pose
        except Exception as e:
            self.get_logger().warn(f'TF lookup failed: {e}')
            return None
    #basically trying to get our status, this is all chat, but some parts were wrong
    #the accurate status definitions are in here:
    #https://docs.ros2.org/foxy/api/action_msgs/msg/GoalStatus.html
    def status_callback(self, msg):
        if len(msg.status_list) == 0:
            self.goal_status = 0
            self.goal_active = False
            return
        self.goal_status = msg.status_list[-1].status
        self.goal_active = (self.goal_status == 1)  # active if status is 1


    def scan_callback(self, msg):
        
        # Because the lidar is oriented backward on the racecar, 
        # if we want the middle value of the ranges to be forward:
        #l2 = len(msg.ranges)/2
        #ranges = msg.ranges[l2:len(msg.ranges)] + msg.ranges[0:l2]
        #this is shit that was here before
        twist = Twist()
        twist.linear.x = float(self.max_speed)
        twist.angular.z = 0.0
          
        self.cmd_vel_pub.publish(twist)
        #x_goal = self.goal_msg.pose.position.x
        #y_goal = self.goal_msg.pose.position.y
        #self.get_logger().info(f"Robot goal: x={x_goal:.3f}, y={y_goal:.3f}")
        self.get_pose()
        #this is the first goal
        if not self.goal_flag:
            self.manage_goal(self.goalx, self.goaly,0.0)
            self.goal_flag = True
        if self.get_pose() is not None:
            #jesus fuck I wrote some spaghetti code here
            #status 4 means that it succeeded its first goal
            #once the goal succeeds, we give it a new goal, which is its first position we calculated in init
            #then max_speed = 0 so it stops moving
            #tolerance matching is to give it some wiggle room so it accepts values that are not exactly equal to the goal
            if self.goal_status == 4 or self.toleranceMatching(self.get_pose().pose.position.x,self.get_pose().pose.position.y, self.goalx, self.goaly):
                self.manage_goal(self.initX, self.initY,0.0)
                self.max_speed = 0

        
        

        #self.goal_pose.publish(self.goal_position)

        #Will's code
        '''
        influence = self.distance
        n = len(msg.ranges)
        if n == 0:
            return

        l2 = n // 2
        ranges_raw = np.array(msg.ranges, dtype=float)
        ranges = np.concatenate((ranges_raw[l2:], ranges_raw[:l2]))

        angles_all = np.linspace(msg.angle_min, msg.angle_max, n)
        angles = np.concatenate((angles_all[l2:], angles_all[:l2]))

        max_range = msg.range_max if msg.range_max > 0 else 10.0
        ranges[np.isinf(ranges)] = max_range
        ranges[ranges == 0] = max_range
        ranges = np.clip(ranges, 0.0, max_range)

        min_r = float(np.min(ranges))

        left_sector  = (angles > math.radians(45)) & (angles < math.radians(135))
        right_sector = (angles < math.radians(-45)) & (angles > math.radians(-135))

        left_dist = np.mean(ranges[left_sector]) if np.any(left_sector) else influence
        right_dist = np.mean(ranges[right_sector]) if np.any(right_sector) else influence

        # error = positive if car too close to left wall
        error = (right_dist - left_dist)

        Kp = 1
        Kd = 0.8
        K_angular = 0.6

        derivative = error - self.prev_error
        angular_cmd = Kp * error + Kd * derivative
        angular_cmd -= K_angular * self.prev_angular_cmd

        angular_cmd = float(np.clip(angular_cmd, -self.max_steering, self.max_steering))
        self.prev_error = error
        self.prev_angular_cmd = angular_cmd

 
        linear_speed = self.max_speed
        if min_r <= self.distance_short:
            linear_speed = 0.15
        else:
            fwd_sector = np.abs(angles) < math.radians(15)
            fwd_mean = np.mean(ranges[fwd_sector]) if np.any(fwd_sector) else min_r
            linear_speed = (fwd_mean / (self.distance * 2.0)) * self.max_speed
            linear_speed = float(np.clip(linear_speed, 0.05, self.max_speed))


        if abs(angular_cmd) > 0.5 * self.max_steering:
            linear_speed *= 0.5

 
        twist = Twist()
        twist.linear.x = float(linear_speed)
        twist.angular.z = angular_cmd  # use PD output directly
        self.cmd_vel_pub.publish(twist)
        '''

    def odom_callback(self, msg):
        self.get_logger().info('Current speed: %f' % msg.twist.twist.linear.x)

def main(args=None):
    rclpy.init(args=args)
    path_following = PathFollowing()
    rclpy.spin(path_following)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
