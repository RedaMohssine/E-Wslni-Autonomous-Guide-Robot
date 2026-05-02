#!/bin/bash
# Map Quality Verification Script

echo "=========================================="
echo "    Map Quality Verification Tool"
echo "=========================================="
echo ""

# Check if maps directory exists
if [ ! -d "maps" ]; then
    echo "❌ Error: maps/ directory not found!"
    echo "   Have you saved a map yet?"
    exit 1
fi

# Check for map files
MAP_COUNT=$(ls maps/*.{pgm,png} 2>/dev/null | wc -l)
if [ $MAP_COUNT -eq 0 ]; then
    echo "❌ Error: No map files found in maps/"
    echo "   Save a map first with:"
    echo "   ros2 run nav2_map_server map_saver_cli -f maps/my_map"
    exit 1
fi

echo "✅ Found $MAP_COUNT map file(s) in maps/"
echo ""

# List all maps
echo "Available maps:"
ls -lh maps/*.{pgm,png,yaml} 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

# Check if ROS2 is running
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "=========================================="
echo "Checking ROS2 System..."
echo "=========================================="
echo ""

# Check if /map topic exists
if ros2 topic list 2>/dev/null | grep -q "^/map$"; then
    echo "✅ /map topic is active"
    
    # Check update rate
    echo ""
    echo "Map update rate:"
    timeout 10 ros2 topic hz /map 2>&1 | grep "average" | head -1
    
    # Get map info
    echo ""
    echo "Map information:"
    timeout 5 ros2 topic echo /map --once 2>/dev/null | grep -E "width:|height:|resolution:" | sed 's/^/  /'
    
else
    echo "⚠️  /map topic not found (SLAM may not be running)"
fi

echo ""

# Check if SLAM is running
if ros2 node list 2>/dev/null | grep -q "slam_toolbox"; then
    echo "✅ SLAM Toolbox is running"
else
    echo "⚠️  SLAM Toolbox not running"
fi

echo ""
echo "=========================================="
echo "Map File Verification"
echo "=========================================="
echo ""

# Check most recent map
LATEST_MAP=$(ls -t maps/*.yaml 2>/dev/null | head -1)
if [ -n "$LATEST_MAP" ]; then
    echo "Latest map: $LATEST_MAP"
    echo ""
    echo "Map parameters:"
    cat "$LATEST_MAP" | sed 's/^/  /'
    echo ""
    
    # Check if image file exists
    IMAGE_FILE=$(grep "^image:" "$LATEST_MAP" | awk '{print $2}')
    IMAGE_PATH="maps/$IMAGE_FILE"
    if [ -f "$IMAGE_PATH" ]; then
        echo "✅ Image file exists: $IMAGE_PATH"
        SIZE=$(du -h "$IMAGE_PATH" | cut -f1)
        echo "   Size: $SIZE"
    else
        echo "❌ Image file not found: $IMAGE_PATH"
    fi
else
    echo "⚠️  No YAML metadata file found"
fi

echo ""
echo "=========================================="
echo "Recommendations"
echo "=========================================="
echo ""

if [ $MAP_COUNT -eq 0 ]; then
    echo "📝 To create a map:"
    echo "   1. Start Gazebo: ros2 launch robot_simulation gazebo_headless.launch.py"
    echo "   2. Start SLAM: ros2 launch robot_simulation slam.launch.py"
    echo "   3. Drive robot around to explore"
    echo "   4. Save map: ros2 run nav2_map_server map_saver_cli -f maps/my_map"
elif ros2 topic list 2>/dev/null | grep -q "^/map$"; then
    echo "📝 SLAM is active - continue exploring!"
    echo "   Drive slowly and rotate frequently for best results"
    echo "   Save when exploration is complete"
else
    echo "✅ Map saved successfully!"
    echo "   You can view it with: eog $IMAGE_PATH"
    echo "   Ready for Step 8: Map Loading"
fi

echo ""
echo "=========================================="
