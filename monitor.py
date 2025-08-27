import docker
import time
import logging

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
CLONE_NUM = 1
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
            #logging.info(f"Paused container '{name}' was successfully.")
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
            clone.remove(force=True)
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
    if "_clone" in container_name:
        base_name = container_name.split("_clone")[0]
    else:
        base_name = container_name

    existing_clones = []
    containers = client.containers.list(all=True)
    for i in containers:
        if i.name.startswith(base_name + "_clone"):
            existing_clones.append(i)


    if len(existing_clones) >= CLONE_NUM:
        logging.info(f"Maximum clones ({CLONE_NUM}) reached for '{base_name}'. Pausing original and deleting all clones.")
        
        try:
            original_container = client.containers.get(base_name)
            original_container.pause()
            logging.info(f"Paused original container '{original_container.name}'.")

        except Exception as Error:
            logging.error(f"Failed to pause or find original container '{base_name}': {Error}")
        delete_clones(container)

        return

    clone_name = f"{base_name}_clone{len(existing_clones) + 1}"

    try:
        original_container = client.containers.get(base_name)
        config = original_container.attrs.get('Config', {})

        image = config.get('Image')
        command = config.get('Cmd')
        environment = config.get('Env')
        ports = config.get('ExposedPorts')

        if not image:
            raise ValueError(f"Original container '{base_name}' has no image defined.")

        new_container = client.containers.run(
            image=image,
            command=command,
            name=clone_name,
            environment=environment,
            ports=ports,
            detach=True
        )
        logging.info(f"Successfully created clone container '{clone_name}'.")
    except Exception as err:
        logging.error(f"Error creating clone container '{clone_name}': {err}")


def monitor():
    #logging.info("Docker Monitor Service started. Monitoring containers...")
    while True:
        containers = client.containers.list()
        for container in containers:
            
            container_name = container.name
            container_status = container.status

            #logging.info(f"Checking container: {container_name}... START")
            #logging.info(f"Container {container_name} status: {container_status}")

            if container_status != 'running' and container_status != 'paused':
                logging.info(f"Restarting inactive container: {container_name}... START")
                try:
                    container.restart()
                    logging.info(f"Container {container_name} restarted successfully.")
                except Exception as Error:
                    logging.error(f"Failed to restart container {container_name}: {Error}")
                #logging.info(f"Restarting inactive container: {name}... DONE")
            else:
                CPU_percent = CPU_usage(container)
                RAM_percent = RAM_usage(container)

                #logging.info(f"Container {container_name} CPU usage: {CPU_percent:.2f}% AND Memory usage: {RAM_percent:.2f}%")
                
                if CPU_percent > CPU_LIMIT or RAM_percent > RAM_LIMIT:
                    if "_clone" in container_name:
                        logging.info(f"Skipping clone container: {container_name}")
                        continue
                    logging.info(f"Container {container_name} overloaded (CPU: {CPU_percent:.2f}%, Memory: {RAM_percent:.2f}%). Attempting to scale...")
                    scale_container(container)
            #logging.info(f"Checking container: {container_name}... DONE")

        logging.info(f"Sleeping {SLEEP_TIME} seconds before next check...")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    logging.info("Starting Docker Monitor Service... you can use Ctrl+C for safly exit")
    try:
        monitor()
    except KeyboardInterrupt:
        logging.info("Docker Monitor Service stopped. Pausing all running containers...")
        containers = client.containers.list()
        for container in containers:
            pause_container(container)
        logging.info("All running containers paused. Exiting cleanly. GoodBy")
        