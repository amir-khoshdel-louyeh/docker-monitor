# Docker Monitor 🐳📊

A lightweight **Docker container monitoring and auto-scaling tool** built with **Python**, **Flask**, and the **Docker SDK**.  
It provides:

- Real-time **CPU and RAM usage** tracking for all containers  
- Automatic **restart of inactive containers**  
- Simple **scaling/cloning** when CPU or RAM usage exceeds thresholds  
- A **web interface** for live monitoring and container control  
- REST API endpoints for automation  

---

## Features ✨
- 📈 **Live container stats** (CPU%, RAM%)  
- 🔄 **Auto-restart** containers if they stop unexpectedly  
- ⚡ **Auto-scale** containers when resource limits are exceeded  
- ⏸️ Pause, restart, unpause, or remove containers directly from the web UI  
- 🔊 **Logs streaming** (live logs available at `/logs`)  
- 🖥️ **Flask web dashboard** (served at `http://localhost:5000`)  

---

## Dependencies 📦

This project requires:

- **Python 3.8+**
- **Docker Engine** installed and running
- Python libraries:
  - `docker`  
  - `flask`  
  - `logging` (standard library)  
  - `threading` (standard library)  
  - `subprocess` (standard library)  
  - `json` (standard library)  
  - `collections` (standard library)  
  - `queue` (standard library)  

Install dependencies with:

```bash
pip install docker flask
```

---

## Getting Started 🚀

1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/docker-monitor.git
   cd docker-monitor
   ```

2. Run the monitor:
   ```bash
   python3 monitor.py
   ```

3. Open the dashboard:
   ```
   http://localhost:5000
   ```
   *(It will also auto-open in your default browser.)*

---

## Configuration ⚙️

You can adjust the monitoring behavior in the script:

- **CPU Limit**: `CPU_LIMIT = 70.0`  
- **RAM Limit**: `RAM_LIMIT = 70.0`  
- **Max Clones**: `CLONE_NUM = 2`  
- **Check Interval**: `SLEEP_TIME = 1` (seconds)  

---

## API Endpoints 📡

- `/` → Web dashboard  
- `/logs` → Returns latest logs in JSON  
- `/container_stats` → Stats for all containers (JSON)  
- `/control` → Control a specific container (pause, unpause, restart, remove)  
- `/control_all` → Apply action to all containers  
- `/stream` → Live event stream (Server-Sent Events)  
- `/kill_remove` → Run kill & remove script  
- `/test_environment` → Run test setup script  

---

## Example Dashboard Screenshot 🖼️
*(Add your screenshot here!)*  

---

## Notes 📝
- Requires Docker daemon access (if running without root, make sure your user is added to the `docker` group).  
- Custom scripts used:  
  - `docker-kill-remove.sh`  
  - `setup_test_env.sh`  
  *(Update paths to match your environment.)*  
