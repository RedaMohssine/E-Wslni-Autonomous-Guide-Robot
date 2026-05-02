cmake_minimum_required(VERSION 3.8)
project(robot_navigation2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)

# Pas besoin de find_package pour nav2 - on utilise les packages système
# find_package(nav2_amcl REQUIRED)
# find_package(nav2_bt_navigator REQUIRED)
# find_package(nav2_controller REQUIRED)
# find_package(nav2_costmap_2d REQUIRED)
# find_package(nav2_navfn_planner REQUIRED)
# find_package(nav2_planner REQUIRED)
# find_package(nav2_recoveries REQUIRED)
# find_package(nav2_lifecycle_manager REQUIRED)
# find_package(nav2_map_server REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(
  DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
