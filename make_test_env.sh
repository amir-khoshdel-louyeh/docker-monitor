#!/bin/bash

echo "Setting up Docker test environment..."

# Run base container
docker run -d --name test-nginx nginx

# Run CPU stress container
docker run -d --name cpu-stress alpine sh -c "while true; do :; done"

# Build and run memory stress container
cat > mem_hog.py <<EOF
import time
a = []
while True:
    a.append(' ' * 10**6)  # allocate ~1MB per iteration
    time.sleep(0.1)
EOF

cat > Dockerfile.memhog <<EOF
FROM python:3.9-alpine
COPY mem_hog.py /mem_hog.py
CMD ["python", "/mem_hog.py"]
EOF

docker build -t memhog -f Dockerfile.memhog .

docker run -d --name mem-stress memhog

# Cleanup build files
rm mem_hog.py Dockerfile.memhog

# Stop base container to test restart
docker stop test-nginx

# Show container statuses
echo "Current container statuses:"
docker ps -a --format "table {{.Names}}\t{{.Status}}"

echo "Test environment ready."

