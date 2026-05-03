# E-Wslni — Autonomous Campus Guide Robot

> **E-Wslni** (وصلني) is Moroccan Darija for *"Take me there"* — an autonomous indoor guide robot developed at [EMINES School of Industrial Management, UM6P](https://www.emines-ingenieur.org/) as a 1-year engineering capstone project.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Modules](#modules)
  - [Hardware & Firmware](#hardware--firmware)
  - [SLAM Mapping](#slam-mapping)
  - [Autonomous Navigation — Nav2](#autonomous-navigation--nav2)
  - [AI Chatbot Interface](#ai-chatbot-interface)
- [In Action](#in-action)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [1 — SLAM Mapping](#1--slam-mapping)
  - [2 — Autonomous Navigation](#2--autonomous-navigation)
  - [3 — Chatbot Interface](#3--chatbot-interface)
- [Project Documents](#project-documents)
- [Repository Structure](#repository-structure)
- [Team](#team)

---

## Overview

E-Wslni is a full-stack autonomous guide robot that lets campus visitors ask questions or request navigation to any location by voice or text. The robot:

1. **Maps** the campus autonomously using a 2D LiDAR and SLAM
2. **Localizes** itself in real-time within that map
3. **Understands** natural-language requests in French, English, and Arabic
4. **Navigates** autonomously to the requested destination using Nav2
5. **Responds** via synthesized speech in the visitor's language

---

## System Architecture

The system is divided into four integrated layers:

| Layer | Technology | Role |
|-------|-----------|------|
| **Hardware** | Arduino Mega 2560 + MPU-6050 | Low-level motor control, odometry, anomaly detection |
| **Compute** | Lenovo ThinkCentre Mini PC, Ubuntu 22.04) | Runs ROS2, SLAM, Nav2, vision |
| **Perception** | LD06 LiDAR + Logitech C920 camera | 360° 2D laser scanning + semantic obstacle detection |
| **Mapping / Navigation** | SLAM Toolbox + Nav2 | Real-time mapping & autonomous path planning |
| **Interface** | Streamlit + LangGraph + GPT-4o-mini | Conversational AI with voice I/O |

Communication between the chatbot (which can run on any machine) and the robot passes through a lightweight **FastAPI WebSocket hub** deployed on Railway.

---

## Modules

### Hardware & Firmware

**File:** [`arduino.ino`](arduino.ino)  
**Hardware:** Arduino Mega 2560, MPU-6050 IMU, 2× DC motors with quadrature encoders, 12 V Li-ion motor battery

The main firmware handles:

- **Differential drive control** — independent left/right DC motors, PWM + PID with feedforward, adaptive filtering
- **Wheel geometry** — wheel radius 0.10 m, wheelbase (entraxe) 0.488 m
- **Odometry** — quadrature encoders (64 CPR) sampled at 128 Hz; velocity published to ROS2 at 57600 baud
- **Anomaly detection** via MPU-6050:
  - Tilt / rollover detection (gyro X/Y rates)
  - Floor bump detection (accelerometer Z deviation from baseline)
  - Wheel-slip detection (gyro yaw vs. encoder-computed yaw divergence); PID gain reduced to 60 % on slip
- **Battery management** — 12 V Li-ion monitoring with relay cutoff at 11 V (motors disconnected during charge)
- **Angular correction loop** — PI controller (Kp=0.8, Ki=1.5) to compensate mechanical asymmetries
- **Serial protocol** — speed + angular velocity commands; telemetry at 128 Hz

**CAD Design:** [`SolidWorks CAD/`](SolidWorks%20CAD/)  
60+ SolidWorks parts and assemblies covering the octagonal chassis (HPL 8 mm panels, steel square-tube frame), motor mounts, wheel sub-assemblies (axle + pillow-block bearings + flexible coupling), LiDAR/screen enclosure, camera support, charging port, and the automatic charging station.

| Real Robot | SolidWorks CAD Model |
|:---:|:---:|
| <img src="images/robot%20image%20.JPG" width="400" alt="E-Wslni — octagonal laser-cut chassis with LD06 LiDAR and electronics box on top"/> | <img src="images/robot%20cad%20screenshot.png" width="400" alt="SolidWorks full-assembly render of E-Wslni showing chassis layers, wheel assembly, and electronics enclosure"/> |
| *The physical robot: octagonal laser-cut chassis, dual DC drive wheels, and the electronics enclosure housing the LD06 LiDAR on top.* | *SolidWorks full assembly — chassis layers, motor mounts, drive wheels, LiDAR mount, and the detachable electronics box.* |

---

### SLAM Mapping

**Directory:** [`Mapping (SLAM)/`](Mapping%20(SLAM)/)  
**Stack:** ROS2 Humble · SLAM Toolbox · LD06 LiDAR · Arduino Uno

The SLAM module builds a persistent 2D occupancy map of the campus while the operator teleoperates the robot.

#### Key files

| File | Role |
|------|------|
| `src/ldlidar_stl_ros2/` | LD06 LiDAR ROS2 driver (C++) — publishes `/scan` at 230400 baud |
| `scripts/arduino_bridge.py` | Reads encoder ticks from Arduino, publishes `/odom` with differential drive kinematics |
| `scripts/keyboard_teleop.py` | AZERTY keyboard teleoperation for manual mapping runs |
| `hardware_r/robot_control.ino` | Arduino Uno sketch used during SLAM (speed + steering protocol) |
| `config/mapper_params_online_async.yaml` | SLAM Toolbox parameters (resolution, range, loop closure) |
| `config/slam_toolbox.rviz` | RViz layout for real-time map visualization |
| `launch/robot_slam_launch.py` | All-in-one launch: LiDAR + Arduino bridge + SLAM Toolbox |

#### TF tree

```
map → odom → base_footprint → base_link → base_laser
```

#### Quick start

```bash
# 1. Give serial permissions (once)
sudo chmod 666 /dev/ttyUSB0 /dev/ttyACM0
# or install persistent udev rules:
sudo bash scripts/create_udev_rules.sh

# 2. Upload robot_control.ino to Arduino Uno via Arduino IDE

# 3. Build the ROS2 workspace
cd "Mapping (SLAM)/ld06_reel_plateforme_mobile/LD06_SLAM_Robot_Clean"
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash

# 4. Launch everything
ros2 launch launch/robot_slam_launch.py

# 5. Teleoperate with AZERTY keyboard (separate terminal)
python3 scripts/keyboard_teleop.py
```

| Key | Action |
|-----|--------|
| `Z` | Forward |
| `S` | Backward |
| `Q` | Turn left |
| `D` | Turn right |
| `Space` | Stop |

#### Save the map

```bash
ros2 run nav2_map_server map_saver_cli -f ~/campus_map
# Produces: campus_map.pgm + campus_map.yaml
```

#### Result — EMINES campus map

![2D occupancy map of the EMINES campus corridors and rooms, generated by SLAM Toolbox with the LD06 LiDAR](images/the%20map%20mapped%20by%20the%20robot.png)

*Full occupancy map of the EMINES building generated during a teleoperated mapping run. White = free space, black = walls/obstacles, grey = unexplored. The map captures the main corridors, room doorways, and open areas across the floor.*

---

### Autonomous Navigation — Nav2

**Directory:** [`Navigation (NAV2)/`](Navigation%20(NAV2)/)  
**Stack:** ROS2 Humble · Nav2 · Gazebo (simulation) · pre-built campus map

The navigation module uses the map saved during SLAM to localize the robot (AMCL) and plan collision-free paths to goal positions sent by the chatbot.

#### Key source packages

| Package | Role |
|---------|------|
| `robot_hardware/` | Translates Nav2 `cmd_vel` → Arduino serial commands; publishes encoder odometry |
| `robot_navigation/` | Nav2 parameter file (`nav2_params.yaml`) and launch |
| `robot_navigation2/` | Alternative Nav2 configurations (localization-only, minimal, complete) |
| `robot_simulation/` | Gazebo world + robot URDF for simulation-based testing |

#### Utility scripts

| Script | Purpose |
|--------|---------|
| `map_scale_calibrator.py` | Interactive GUI — click known distances on the PGM map to calibrate resolution |
| `teamviewer.py` | Terminal HUD with real-time speed/turn bars for manual control |

#### Nav2 in action — local costmap and trajectory planning

![Nav2 local costmap overlaid on the campus map, with the planned trajectory shown through a corridor](images/map%20with%20the%20costmap.png)

*Nav2 running on the real robot: the coloured overlay is the **local costmap** (inflation layers around obstacles in green/brown), and the planned **trajectory** shows the route the robot is following through the corridor. The DWB planner replans dynamically at each control step.*

#### Quick start (real robot)

```bash
cd "Navigation (NAV2)/slam"
source /opt/ros/humble/setup.bash
source test/install/setup.bash

# Launch navigation with saved map
ros2 launch robot_hardware real_robot_nav.launch.py map:=test/maps/slam_map.yaml
```

#### Quick start (simulation)

```bash
cd "Navigation (NAV2)/slam/test"
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch robot_simulation gazebo.launch.py
ros2 launch robot_navigation2 nav2.launch.py use_sim_time:=true
```

---

### AI Chatbot Interface

**Directory:** [`UI + Chatbot/`](UI%20+%20Chatbot/)  
**Stack:** Streamlit · LangGraph · LangChain · OpenAI GPT-4o-mini · Whisper · Cartesia · Chroma · FastAPI

The chatbot is a Streamlit web application that gives visitors a conversational interface — by text or voice — to query the campus knowledge base and request autonomous navigation.

#### Architecture

```
User (browser)
    │  voice / text
    ▼
Streamlit UI  ──────────────────────────────────────┐
    │                                                │
    ▼                                                │
LangGraph Workflow                                   │
    ├─ AudioWorkflow: STT (Whisper) → LLM → TTS     │
    └─ ChatWorkflow:  text → LLM                     │
              │                                      │
              ▼                                      │
         GPT-4o-mini (tool use)                      │
          ├─ document_retriever  ←── Chroma RAG      │
          └─ navigation_tool                         │
                    │                                │
                    ▼                                │
            FastAPI Hub (Railway) ◄──────────────────┘
                    │
                    ▼
              Robot (Nav2 goal)
```

#### User Interface

![Streamlit chatbot UI — destination search panel, locations list, robot status card, and the voice/chat assistant widget](images/UI%20screenshot%20with%20explanations.png)

*The desktop interface — **"Navigateur Robot Universitaire"**:*
- **(Left) Location browser** — searchable list of all 19+ campus destinations, filterable by category (Administrative, Food, Labs, Clubs…). Click any card to select it.*
- **(Top-right) Destination panel** — shows details of the selected destination and triggers navigation on the robot.*
- **(Mid-right) Robot status** — live connection status, battery level, and current position reported by the robot.*
- **(Bottom-right) AI Assistant** — switch between **Chat** (text) and **Voice** modes. Voice input is transcribed by Whisper, answered by GPT-4o-mini in the visitor's language (FR/EN/AR), and spoken back through the robot's speaker via Cartesia TTS.*

#### Key files

| File | Role |
|------|------|
| `streamlit_app.py` | Entry point |
| `src/workflow.py` | LangGraph state machine — routes audio/text, calls tools |
| `src/services/llm.py` | GPT-4o-mini agent with two tools: RAG retrieval + navigation dispatch |
| `src/services/navigation.py` | Fuzzy location matching + WebSocket dispatch to robot |
| `src/services/rag.py` | OpenAI embeddings + Chroma vector search over campus docs |
| `src/services/stt.py` | Whisper-1 speech-to-text with campus proper-noun prompt biasing |
| `src/services/tts.py` | Cartesia text-to-speech (French/English/Arabic routing) |
| `src/services/memory.py` | Conversation history persistence |
| `src/ui/app_desktop.py` | Main Streamlit page — chat widget, voice orb, navigation card |
| `hub/main.py` | FastAPI WebSocket relay between chatbot and robot |
| `vectordb_generation.py` | One-time script to index campus documents into Chroma |
| `data/locations.json` | Campus destinations catalog (name, aliases, coordinates, category) |
| `data/*.md` | EMINES programs and campus knowledge base |

#### Setup

```bash
cd "UI + Chatbot"
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
ASSEMBLYAI_API_KEY=...
CARTESIA_API_KEY=...
HUB_URL=wss://your-hub.railway.app/ws/robot   # optional: only for live robot
HUB_TOKEN=...                                   # optional
```

Build the RAG index (first time only):

```bash
python vectordb_generation.py
```

Run the app:

```bash
streamlit run streamlit_app.py
```

#### Deploy the hub (Railway)

```bash
cd hub
# Push to Railway — Procfile and railway.json are included
```

---

## In Action

The robot navigating autonomously through EMINES corridors and doorways:

| Approaching a doorway | Crossing through |
|:---:|:---:|
| ![E-Wslni approaching an open doorway in an EMINES corridor, aligned by the Nav2 local planner](images/robot%20near%20to%20a%20door.png) | ![E-Wslni successfully crossing through a doorway, demonstrating narrow-passage navigation](images/robot%20crossing%20a%20door.png) |
| *Robot approaching an open doorway — the Nav2 local planner aligns the robot with the gap while continuously replanning around the door-frame obstacle.* | *Robot threading through the doorway — demonstrating the clearance margins achieved by the DWB planner and the differential drive kinematics.* |

---

## Tech Stack

| Domain | Technology |
|--------|-----------|
| Robot OS | ROS2 Humble (Ubuntu 22.04) |
| SLAM | SLAM Toolbox |
| Navigation | Nav2 (costmaps, DWB planner, AMCL) |
| Simulation | Gazebo |
| LiDAR | LD06 (12 m range, 360°, 10 Hz) |
| Microcontroller | Arduino Mega 2560 |
| IMU | MPU-6050 (gyro + accelerometer) |
| LLM | OpenAI GPT-4o-mini |
| Orchestration | LangChain + LangGraph |
| Vector DB | Chroma |
| STT | OpenAI Whisper-1 |
| TTS | Cartesia |
| UI Framework | Streamlit |
| Hub | FastAPI + WebSockets (Railway) |
| CAD | SolidWorks |
| Languages | Python 3.11 · C++ · C (Arduino) |

---

## Getting Started

### Prerequisites

- **Ubuntu 22.04** for the robot (ROS2 / Nav2)
- **Python 3.11+** for the chatbot (any OS)
- **ROS2 Humble** — [install guide](https://docs.ros.org/en/humble/Installation.html)
- **Arduino IDE** — for firmware upload
- API keys: OpenAI, Cartesia

### 1 — SLAM Mapping

See [SLAM Mapping](#slam-mapping) section above.

### 2 — Autonomous Navigation

See [Autonomous Navigation](#autonomous-navigation--nav2) section above.

### 3 — Chatbot Interface

See [AI Chatbot Interface](#ai-chatbot-interface) section above.

---

## Project Documents

The full technical documentation for this project is included at the root of the repository:

| Document | Description |
|----------|-------------|
| [📄 Dossier de définition](Dossier%20de%20d%C3%A9finition.pdf) | Project definition document — functional requirements, system specifications, design choices, and technical architecture |
| [📊 Présentation soutenance 2](Pr%C3%A9sentation%20soutenance%202%20guide%20intelligent.pdf) | Final presentation slides — project overview, results, and demonstrations |

---

## Repository Structure

```
Autonomous-Guide-Robot-E-Wslni/
│
├── arduino.ino                          # Arduino Mega 2560 main firmware
├── Dossier de définition.pdf            # Project definition document
├── Présentation soutenance 2 guide intelligent.pdf
│
├── images/                              # Project photos and screenshots
│   ├── robot image .JPG                 # Physical robot photo
│   ├── robot cad screenshot.png         # SolidWorks CAD render
│   ├── the map mapped by the robot.png  # SLAM occupancy map result
│   ├── map with the costmap.png         # Nav2 costmap + trajectory
│   ├── UI screenshot with explanations.png  # Annotated chatbot UI
│   ├── robot near to a door.png         # Robot approaching a doorway
│   ├── robot crossing a door.png        # Robot crossing a doorway
│   └── photo of our team and professors.JPG # Team photo
│
├── SolidWorks CAD/                      # 60+ mechanical parts & assemblies
│
├── Mapping (SLAM)/
│   └── ld06_reel_plateforme_mobile/
│       └── LD06_SLAM_Robot_Clean/
│           ├── src/ldlidar_stl_ros2/    # LD06 LiDAR ROS2 driver (C++)
│           ├── scripts/
│           │   ├── arduino_bridge.py    # Odometry publisher (Ackermann kinematics)
│           │   └── keyboard_teleop.py   # Manual AZERTY teleoperation
│           ├── config/                  # SLAM Toolbox + RViz configs
│           ├── launch/                  # ROS2 launch files
│           └── hardware_r/
│               └── robot_control.ino    # Arduino Uno SLAM-mode firmware
│
├── Navigation (NAV2)/
│   └── slam/
│       ├── map_scale_calibrator.py      # Map resolution calibration GUI
│       ├── teamviewer.py                # Interactive terminal controller
│       └── test/src/
│           ├── robot_hardware/          # cmd_vel → Arduino, encoder odometry
│           ├── robot_navigation/        # Nav2 parameter files
│           ├── robot_navigation2/       # Nav2 launch configurations
│           └── robot_simulation/        # Gazebo world + robot URDF
│
└── UI + Chatbot/
    ├── streamlit_app.py                 # Entry point
    ├── vectordb_generation.py           # RAG index builder
    ├── hub/main.py                      # FastAPI WebSocket relay (Railway)
    ├── src/
    │   ├── workflow.py                  # LangGraph state machine
    │   ├── models.py                    # Data models
    │   ├── services/                    # LLM · RAG · STT · TTS · Navigation · Memory
    │   ├── ui/                          # Streamlit pages & CSS
    │   └── components/                  # Custom voice orb component
    └── data/
        ├── locations.json               # Campus destinations catalog
        └── *.md                         # EMINES campus knowledge base
```

---

## Team

Developed at **EMINES School of Industrial Management — UM6P** (2024–2025).

![The E-Wslni project team and supervising professors gathered around the robot at EMINES, UM6P, Ben Guerir](images/photo%20of%20our%20team%20and%20professors.JPG)

*The E-Wslni team and supervising professors at EMINES — Université Mohammed VI Polytechnique, Ben Guerir, Morocco.*

<!-- Add your team members here -->
<!--
| Name | Role |
|------|------|
| ... | ... |
-->

---

*EMINES — École De Management Industriel, Université Mohammed VI Polytechnique, Ben Guerir, Morocco.*
