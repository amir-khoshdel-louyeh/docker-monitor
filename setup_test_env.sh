#!/bin/bash

echo "Setting up Docker test environment..."

# Run base container
docker run -d --name test-nginx nginx

# Run CPU stress container
docker run -d --name cpu-stress alpine sh -c "while true; do :; done"

# Nginx 
docker run -d --name my-nginx -p 8080:80 nginx:alpine 


# Apache 
docker run -d --name my-apache -p 8081:80 httpd:alpine 


# Redis 
docker run -d --name my-redis -p 6379:6379 redis:alpine

# Show container statuses
echo "Current container statuses:"
docker ps -a --format "table {{.Names}}\t{{.Status}}"

echo "Test environment ready."
