#!/bin/bash

# ==========================================
# MASTER SETUP & LAUNCH SCRIPT
# Custom Mobile Robot Navigation System
# ==========================================

set -e  # Exit on error

# 1. DEFINE YOUR WORKSPACE
WS_DIR=~/slam/test

echo "========================================="
echo "Robot Navigation System Launcher"
echo "========================================="

# 2. SOURCE THE ENVIRONMENT FIRST (needed for colcon)
echo "Sourcing ROS2 environment..."
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH  # Clear old paths
source /opt/ros/humble/setup.bash

# 3. KILL ANY EXISTING PROCESSES
echo "Cleaning up old processes..."
pkill -9 -f gazebo 2>/dev/null || true
pkill -9 -f rviz2 2>/dev/null || true
sleep 1

# 4. BUILD THE WORKSPACE
echo "Building workspace..."
cd "$WS_DIR"
colcon build --packages-select robot_description robot_navigation2 robot_simulation

# Check if build succeeded
if [ $? -eq 0 ]; then
  echo "✓ Build successful."
else
  echo "✗ Build failed! Stopping."
  exit 1
fi

# 5. SOURCE THE LOCAL WORKSPACE
echo "Sourcing workspace environment..."
source "$WS_DIR/install/setup.bash"

# 5. LAUNCH THE SIMULATION
echo "========================================="
echo "Launching Robot Navigation System..."
echo "========================================="
echo ""
echo "Gazebo should start..."
echo "RViz2 should open..."
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
ros2 launch robot_navigation2 run_simulation.launch.py use_sim_time:=true
