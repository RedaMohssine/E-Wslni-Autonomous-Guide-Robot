#!/bin/bash

# ==========================================
# REAL ROBOT NAVIGATION LAUNCH SCRIPT
# ==========================================
# This script builds and launches the real robot navigation system.
# It does NOT start Gazebo — it connects to real hardware.
#
# Usage:
#   ./launch_real_robot.sh               # Default map
#   ./launch_real_robot.sh /path/to/map.yaml  # Custom map
# ==========================================

set -e  # Exit on error

# 1. DEFINE YOUR WORKSPACE
WS_DIR=~/slam/test

echo "========================================="
echo "REAL Robot Navigation System Launcher"
echo "========================================="
echo ""
echo "⚠️  This launches the REAL robot!"
echo "⚠️  Make sure Arduino is connected and encoders/LiDAR are running."
echo ""

# 2. SOURCE THE ENVIRONMENT
echo "Sourcing ROS2 environment..."
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH  # Clear old paths
source /opt/ros/humble/setup.bash

# 3. BUILD THE WORKSPACE
echo "Building workspace..."
cd "$WS_DIR"
colcon build --packages-select robot_description robot_hardware

# Check if build succeeded
if [ $? -eq 0 ]; then
  echo "✓ Build successful."
else
  echo "✗ Build failed! Stopping."
  exit 1
fi

# 4. SOURCE THE LOCAL WORKSPACE
echo "Sourcing workspace environment..."
source "$WS_DIR/install/setup.bash"

# 5. OPTIONAL: Set the map file
MAP_ARG=""
if [ -n "$1" ]; then
  MAP_ARG="map:=$1"
  echo "Using custom map: $1"
else
  echo "Using default map (from robot_simulation package)"
fi

# 6. LAUNCH
echo "========================================="
echo "Launching Real Robot Navigation System..."
echo "========================================="
echo ""
echo "WHAT'S RUNNING:"
echo "  • robot_state_publisher  (URDF TF tree)"
echo "  • cmd_vel_to_arduino     (Nav2 → Arduino motors)"
echo "  • encoder_odometry       (Encoders → /odom + TF)"
echo "  • map_server             (Saved map)"
echo "  • AMCL                   (Localization)"
echo "  • Nav2 stack             (Planner + Controller + Behaviors)"
echo "  • RViz2                  (Visualization)"
echo ""
echo "NAVIGATION INSTRUCTIONS:"
echo "1. In RViz2, click '2D Pose Estimate'"
echo "2. Click on the map where robot is"
echo "3. Draw arrow to show robot orientation"
echo "4. Click '2D Nav Goal' to send destination"
echo "5. Robot should navigate autonomously!"
echo ""
echo "========================================="
echo ""

cd "$WS_DIR"
ros2 launch robot_hardware real_robot_nav.launch.py $MAP_ARG
