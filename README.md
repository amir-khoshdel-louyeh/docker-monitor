# DocMan 🐳📊

A powerful desktop tool for monitoring and managing Docker containers, built with Python and Tkinter.

This application provides a native graphical interface for live monitoring and management of your Docker containers, including:

- Real-time resource tracking (CPU & RAM).
- Auto-scaling of services when resource limits are exceeded.
- An integrated terminal for running Docker commands directly.

---

## Features ✨
- 📈 **Live container stats** (CPU%, RAM%)  
- ⚡ **Auto-scale** containers when resource limits are exceeded  
- ⏯️ **Manage containers**: Stop, Pause, Unpause, Restart, and Remove containers directly from the UI.
- 🎛️ **Global controls**: Apply actions to all containers at once.
- 🖥️ **Embedded Terminal**: A secure terminal for running `docker` commands.
- 📝 **Live Application Logs**: See what the monitor is doing in real-time.
- ⚙️ **Dynamic Configuration**: Adjust CPU/RAM limits and other settings without restarting the app.

---

## Installation 🚀

### Option 1: Install from PyPI (Recommended)
```bash
pip install docker-monitor-manager
```

### Option 2: Install from Source
```bash
git clone https://github.com/amir-khoshdel-louyeh/docker-monitor-manager.git
cd docker-monitor-manager
pip install .
```

### Prerequisites
- **Python 3.8+**
- **Docker Engine** (must be installed and running)

## Usage 

After installation, you can run Docker Manager from anywhere using either command:

```bash
# Full package name
docker-monitor-manager

# Or short command
dmm
```

### Development Setup

If you want to contribute or modify the source code:

### 1. Clone the Repository
```bash
git clone https://github.com/amir-khoshdel-louyeh/docker-monitor-manager.git
cd docker-monitor-manager
```

### 2. Create and Activate a Virtual Environment

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install in Development Mode
```bash
pip install -e .
```

## Configuration ⚙️
**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

You can adjust the monitoring behavior in the script:
### 3. Install Dependencies
Install the required Python packages from `requirements.txt`.
```bash
pip install -r requirements.txt
```

- **CPU Limit**: `CPU_LIMIT = 70.0`  
- **RAM Limit**: `RAM_LIMIT = 70.0`  
- **Max Clones**: `CLONE_NUM = 2`  
- **Check Interval**: `SLEEP_TIME = 1` (seconds)  
### 4. Run the Application
Launch the Tkinter application.
```bash
python3 app_tkinter.py
```

---

## API Endpoints 📡
## Configuration ⚙️

- `/` → Web dashboard  
- `/logs` → Returns latest logs in JSON  
- `/container_stats` → Stats for all containers (JSON)  
- `/control` → Control a specific container (pause, unpause, restart, remove)  
- `/control_all` → Apply action to all containers  
- `/stream` → Live event stream (Server-Sent Events)  
- `/kill_remove` → Run kill & remove script  
- `/test_environment` → Run test setup script  
You can adjust the monitoring behavior by clicking the **"Config"** button within the application. This allows you to dynamically change:

---
- **CPU Limit (%)**
- **RAM Limit (%)**
- **Max Clones**
- **Check Interval (s)**

## Example Dashboard Screenshot 🖼️
*(Add your screenshot here!)*  

---

## Notes 📝
- Requires Docker daemon access (if running without root, make sure your user is added to the `docker` group).  
- Custom scripts used:  
