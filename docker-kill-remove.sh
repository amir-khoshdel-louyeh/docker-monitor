#!/bin/bash

# Get all running container IDs
container_ids=$(docker ps -q)

if [ -z "$container_ids" ]; then
  echo "No running containers found. Try to delete all stop ones."
  echo `docker rm $(docker ps -aq)`
  exit 0
fi

for container_id in $container_ids; do
  echo "Processing container: $container_id"

  # Find containerd-shim process related to container
  pids=$(ps aux | grep "$container_id" | grep containerd-shim | awk '{print $2}')

  if [ -z "$pids" ]; then
    echo "No containerd-shim process found for $container_id"
  else
    echo "Killing containerd-shim process(es): $pids"
    sudo kill -9 $pids
  fi

  echo "Removing container $container_id"
  sudo docker rm -f "$container_id"
done

