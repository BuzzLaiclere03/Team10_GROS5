import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/racecar/ros2_ws/src/Team10_GROS5/install/racecar_navigation'
