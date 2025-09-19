import docker
import time
import logging
from collections import deque
import queue
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
import threading
import socket
import webbrowser
import subprocess
import json
import concurrent.futures
import argparse




log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

client = docker.from_env()

try:
    containers = client.containers.list()
    print("Docker client connected successfully!")
    print(f"Found {len(containers)} running container(s).")
except Exception as Error:
    print("Docker client failed to connect.")
    print("Error:", Error)


CPU_LIMIT = 70.0
RAM_LIMIT = 70.0
CLONE_NUM = 2
SLEEP_TIME = 1

def CPU_usage(container):
    try:
        stats = container.stats(stream=False)

        cpu_current = stats['cpu_stats']['cpu_usage']['total_usage']
        cpu_prev = stats['precpu_stats']['cpu_usage']['total_usage']
       
        system_current = stats['cpu_stats']['system_cpu_usage']
        system_prev = stats['precpu_stats']['system_cpu_usage']

        cpu_delta = cpu_current - cpu_prev
        system_delta = system_current - system_prev

        num_cpus = stats['cpu_stats'].get('online_cpus', 1)

        if system_delta > 0 and cpu_delta > 0:
            CPU_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        else:
            CPU_percent = 0.0

        return CPU_percent

    except Exception as Error:
        logging.error(f"Error calculating CPU usage: {Error}")
        return 0.0

def RAM_usage(container):
    try:
        stats = container.stats(stream=False)

        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 1)

        RAM_percent = (mem_usage / mem_limit) * 100.0
        return RAM_percent

    except Exception as Error:
        logging.error(f"Error calculating memory usage: {Error}")
        return 0.0


def pause_container(container):
    name = container.name 
    try:
        if container.status == 'running':
            container.pause()
    except Exception as Error:
        logging.error(f"Failed to pause container '{name}': {Error}")



def delete_clones(container):
    container_name = container.name
    if "_clone" in container_name:
        base_name = container_name.split("_clone")[0]
    else:
        base_name = container_name

    existing_clones = []
    containers = client.containers.list(all=True)
    for i in containers:
        if i.name.startswith(base_name + "_clone"):
            existing_clones.append(i)

    for clone in existing_clones:
        clone_name = clone.name
        try:
            clone.stop()
            clone.remove()
            logging.info(f"Deleted clone container {clone_name}.")
        except Exception as Error:
            logging.error(f"Failed to delete clone container {clone_name}: {Error}")
            try:
                clone.pause()
                logging.info(f"Paused clone container {clone_name} as fallback.")
            except Exception as Error:
                logging.error(f"Failed to pause clone container {clone_name}: {Error}")




def scale_container(container):
    container_name = container.name
    existing_clones = []
    containers = client.containers.list(all=True)
    for c in containers:
        if c.name.startswith(container_name + "_clone"):
            existing_clones.append(c)

    if len(existing_clones) >= CLONE_NUM:
        logging.info(f"Maximum clones ({CLONE_NUM}) reached for '{container_name}'. Pausing original and deleting all clones.")
        try:
            container.pause()
            logging.info(f"Paused original container '{container_name}'.")
        except Exception as Error:
            logging.error(f"Failed to pause original container '{container_name}': {Error}")
        delete_clones(container)
        return

    clone_name = f"{container_name}_clone{len(existing_clones) + 1}"

    try:
        temp_image = container.commit()

        new_container = client.containers.run(
            image=temp_image.id,
            name=clone_name,
            detach=True
        )
        logging.info(f"Successfully created clone container '{clone_name}'.")
    except Exception as Error:
        logging.error(f"Error creating clone container '{clone_name}': {Error}")



def monitor():
    while True:
        containers = client.containers.list(all=True)
        for container in containers:
            
            container_name = container.name
            container_status = container.status

            logging.info(f"Checking container: {container_name}... START")

            if False: #container_status != 'running' and container_status != 'paused'
                logging.info(f"Restarting inactive container: {container_name}... START")
                try:
                    container.restart()
                    logging.info(f"Container {container_name} restarted successfully.")
                except Exception as Error:
                    logging.error(f"Failed to restart container {container_name}: {Error}")
            else:
                CPU_percent = CPU_usage(container)
                RAM_percent = RAM_usage(container)

                record = {'name': container.name,'status': container.status,'cpu': f"{CPU_percent:.2f}",'ram': f"{RAM_percent:.2f}"}
                event_queue.put(record)

                
                if CPU_percent > CPU_LIMIT or RAM_percent > RAM_LIMIT:
                    if "_clone" in container_name:
                        logging.info(f"Skipping clone container: {container_name}")
                        continue
                    logging.info(f"Container {container_name} overloaded (CPU: {CPU_percent:.2f}%, Memory: {RAM_percent:.2f}%). Attempting to scale...")
                    scale_container(container)

        time.sleep(SLEEP_TIME)




app = Flask(__name__)

log_buffer = deque(maxlen=1000)

class BufferHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_buffer.append(log_entry)

buffer_handler = BufferHandler()
buffer_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

if not any(isinstance(h, BufferHandler) for h in logging.getLogger().handlers):
    logging.getLogger().addHandler(buffer_handler)


event_queue = queue.Queue()



@app.route('/logs')
def get_logs():
    return jsonify(list(log_buffer))



@app.route('/')
def home():
    containers = client.containers.list(all=True)
    container_stats = []
    for container in containers:
        try:
            cpu = CPU_usage(container)
            ram = RAM_usage(container)
        except Exception:
            cpu, ram = 0.0, 0.0
        container_stats.append({
            'name': container.name,
            'status': container.status,
            'cpu': f"{cpu:.2f}",
            'ram': f"{ram:.2f}"
        })
    return render_template('index.html', containers=container_stats)




@app.route('/container_stats')
def container_stats():
    containers = client.containers.list(all=True)
    stats = []
    for c in containers:
        try:
            cpu = CPU_usage(c)
            ram = RAM_usage(c)
        except:
            cpu = 0.0
            ram = 0.0
        stats.append({'name': c.name,'status': c.status,'cpu': f"{cpu:.2f}",'ram': f"{ram:.2f}"})
    return jsonify(stats)



@app.route('/control', methods=['POST'])
def control():
    action = request.json.get('action')
    name = request.json.get('name')
    try:
        container = client.containers.get(name)
        if action == 'pause':
            container.pause()
        elif action == 'unpause':
            container.unpause()
        elif action == 'restart':
            container.restart()
        elif action == 'remove':
            container.stop()
            container.remove()
        elif action == 'stop':
            container.stop()
        else:
            return jsonify({'status': 'error', 'message': 'Unknown action'}), 400

        logging.info(f"User requested '{action}' on container '{name}'.")
        return jsonify({'status': 'success'})
    except Exception as Error:
        logging.error(f"Error during '{action}' on container '{name}': {Error}")
        return jsonify({'status': 'error', 'message': str(Error)}), 500




@app.route('/control_all', methods=['POST'])
def control_all():
    action = request.json.get('action')
    try:
        containers = client.containers.list(all=True)
        for container in containers:
            if action == 'pause' and container.status == 'running':
                container.pause()
            elif action == 'unpause' and container.status == 'paused':
                container.unpause()
            elif action == 'stop' and container.status == 'running':
                container.stop()
            elif action == 'restart':
                container.restart()
            elif action == 'remove':
                container.stop()
                container.remove()
        logging.info(f"User requested '{action}' on ALL containers.")
        return jsonify({'status': f'{action.capitalize()} All executed'})
    except Exception as Error:
        logging.error(f"Error during '{action}' on all containers: {Error}")
        return jsonify({'status': 'error', 'message': str(Error)}), 500





@app.route('/run_command', methods=['POST'])
def run_command():
    """
    Executes a shell command.
    SECURITY WARNING: This is a powerful feature. It is restricted to 'docker run'
    to prevent arbitrary code execution, but still poses a risk.
    """
    command_str = request.json.get('command')
    if not command_str:
        return jsonify({'status': 'error', 'message': 'No command provided', 'output': ''}), 400

    # Basic security check to only allow 'docker run'
    if not command_str.strip().startswith('docker run'):
        msg = "Security error: Only 'docker run' commands are allowed."
        logging.warning(msg)
        return jsonify({'status': 'error', 'message': msg, 'output': ''}), 403

    try:
        logging.info(f"Executing user command: {command_str}")
        result = subprocess.run(command_str, shell=True, check=True, capture_output=True, text=True)
        return jsonify({'status': 'success', 'message': 'Command executed', 'output': result.stdout or result.stderr})
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e.stderr}")
        return jsonify({'status': 'error', 'message': 'Command failed', 'output': e.stderr}), 500


@app.route('/stream')
def stream():
    def event_stream():
        while True:
            record = event_queue.get()
            yield f"data: {json.dumps(record)}\n\n"
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")




def open_browser(port):
    """Opens the default web browser to the specified URL."""
    url = f'http://127.0.0.1:{port}/'
    try:
        webbrowser.open_new(url)
    except Exception as e:
        logging.warning(f"Could not open browser: {e}")

    
def run_flask(port, no_browser):
    if not no_browser:
        threading.Timer(1.25, open_browser, args=[port]).start()
    logging.info(f"Dashboard available at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Docker Monitor")
    parser.add_argument('--port', type=int, default=5000, help='Port to run the web server on.')
    parser.add_argument('--no-browser', action='store_true', help="Don't open a web browser automatically.")
    args = parser.parse_args()

    threading.Thread(target=monitor, daemon=True).start()
    run_flask(port=args.port, no_browser=args.no_browser)