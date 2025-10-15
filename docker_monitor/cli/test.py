#!/usr/bin/env python3
"""
dmm-test: Create test Docker containers for testing docker-monitor-manager

This tool creates various test containers to verify that the app works correctly:
- Normal containers (nginx, redis, postgres)
- CPU-intensive containers (stress test)
- Memory-intensive containers (memory hog)
- Containers that can be cloned
- Stopped containers
- Containers with various states
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from typing import List


class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def run_docker(args: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a docker command"""
    cmd = ['docker'] + args
    try:
        if capture:
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        else:
            return subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"{Colors.RED}Error running docker command: {e}{Colors.ENDC}")
        return subprocess.CompletedProcess(cmd, returncode=1, stdout='', stderr=str(e))


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")


def print_status(name: str, status: str, extra: str = ""):
    """Print container creation status"""
    icon = f"{Colors.GREEN}✓{Colors.ENDC}" if status == "created" else f"{Colors.YELLOW}⚠{Colors.ENDC}"
    print(f"{icon} {name}: {status}")
    if extra:
        print(f"  {Colors.CYAN}→{Colors.ENDC} {extra}")


def cleanup_existing_test_containers():
    """Remove existing test containers"""
    print_header("Cleaning up existing test containers")
    
    test_prefixes = ['dmm-test-', 'test-nginx', 'cpu-stress', 'mem-stress']
    
    # Get all containers (including stopped)
    result = run_docker(['ps', '-a', '--format', '{{.Names}}'])
    if result.returncode != 0:
        print(f"{Colors.RED}Failed to list containers{Colors.ENDC}")
        return
    
    containers = result.stdout.strip().split('\n')
    removed_count = 0
    
    for container in containers:
        if not container:
            continue
        # Check if it matches any test prefix
        if any(container.startswith(prefix) for prefix in test_prefixes):
            print(f"Removing: {container}")
            run_docker(['rm', '-f', container], capture=False)
            removed_count += 1
    
    if removed_count > 0:
        print(f"\n{Colors.GREEN}✓ Removed {removed_count} test container(s){Colors.ENDC}")
    else:
        print(f"{Colors.CYAN}No test containers found{Colors.ENDC}")


def create_normal_containers():
    """Create normal working containers"""
    print_header("Creating normal containers")
    
    containers = [
        ('dmm-test-nginx', 'nginx:alpine', 'Web server', ['-p', '8080:80']),
        ('dmm-test-redis', 'redis:alpine', 'Redis cache', ['-p', '6379:6379']),
        ('dmm-test-postgres', 'postgres:alpine', 'PostgreSQL database', 
         ['-e', 'POSTGRES_PASSWORD=test123', '-p', '5432:5432']),
    ]
    
    for name, image, desc, extra_args in containers:
        # Pull image first
        print(f"Pulling image: {image}")
        run_docker(['pull', image], capture=False)
        
        # Create container
        cmd_args = ['run', '-d', '--name', name] + extra_args + [image]
        result = run_docker(cmd_args)
        
        if result.returncode == 0:
            print_status(name, "created", desc)
        else:
            print_status(name, "failed", result.stderr.strip())


def create_cpu_stress_container():
    """Create a CPU-intensive container"""
    print_header("Creating CPU stress container")
    
    name = 'dmm-test-cpu-stress'
    
    # Use alpine with a CPU stress loop
    cpu_stress_cmd = "sh -c 'echo Starting CPU stress; i=0; while true; do i=$((i+1)); done'"
    
    result = run_docker([
        'run', '-d',
        '--name', name,
        '--cpus', '0.5',  # Limit to 0.5 CPU to avoid system overload
        'alpine',
        'sh', '-c',
        'echo "CPU Stress Test Started"; while true; do :; done'
    ])
    
    if result.returncode == 0:
        print_status(name, "created", "CPU-intensive workload (limited to 0.5 CPU)")
    else:
        print_status(name, "failed", result.stderr.strip())


def create_memory_stress_container():
    """Create a memory-intensive container"""
    print_header("Creating memory stress container")
    
    name = 'dmm-test-mem-stress'
    
    # Use Python to allocate memory gradually
    mem_script = '''
import time
import sys

print("Memory stress test started")
sys.stdout.flush()

memory_hog = []
iteration = 0

while True:
    try:
        # Allocate 10MB per iteration
        chunk = ' ' * (10 * 1024 * 1024)
        memory_hog.append(chunk)
        iteration += 1
        
        if iteration % 10 == 0:
            print(f"Allocated ~{iteration * 10}MB")
            sys.stdout.flush()
        
        time.sleep(1)
    except MemoryError:
        print("Memory limit reached")
        sys.stdout.flush()
        time.sleep(60)
        break
'''
    
    # Create container with memory limit
    result = run_docker([
        'run', '-d',
        '--name', name,
        '--memory', '256m',  # Limit to 256MB
        '--memory-swap', '256m',  # No swap
        'python:3.9-alpine',
        'python', '-c', mem_script
    ])
    
    if result.returncode == 0:
        print_status(name, "created", "Memory-intensive workload (limited to 256MB)")
    else:
        print_status(name, "failed", result.stderr.strip())


def create_cloneable_containers():
    """Create containers that demonstrate cloning capability"""
    print_header("Creating containers for clone testing")
    
    # Create a simple container that can be cloned
    base_name = 'dmm-test-clone-base'
    
    # Pull alpine image
    run_docker(['pull', 'alpine:latest'], capture=False)
    
    # Create base container
    result = run_docker([
        'run', '-d',
        '--name', base_name,
        'alpine',
        'sh', '-c', 'echo "Clone Base Container"; sleep infinity'
    ])
    
    if result.returncode == 0:
        print_status(base_name, "created", "Base container for cloning")
        
        # Create a clone manually to demonstrate
        clone_name = 'dmm-test-clone-1'
        
        # Commit the container to an image
        commit_result = run_docker(['commit', base_name, 'dmm-clone-image'])
        
        if commit_result.returncode == 0:
            # Create clone from the committed image
            clone_result = run_docker([
                'run', '-d',
                '--name', clone_name,
                'dmm-clone-image',
                'sh', '-c', 'echo "Cloned Container"; sleep infinity'
            ])
            
            if clone_result.returncode == 0:
                print_status(clone_name, "created", "Cloned from base container")
            else:
                print_status(clone_name, "failed", clone_result.stderr.strip())
    else:
        print_status(base_name, "failed", result.stderr.strip())


def create_stopped_container():
    """Create a stopped container"""
    print_header("Creating stopped container")
    
    name = 'dmm-test-stopped'
    
    # Create and immediately stop
    result = run_docker([
        'run', '-d',
        '--name', name,
        'alpine',
        'echo', 'This container is stopped'
    ])
    
    if result.returncode == 0:
        time.sleep(1)  # Wait for container to stop naturally
        print_status(name, "created", "Container is stopped (for restart testing)")
    else:
        print_status(name, "failed", result.stderr.strip())


def show_container_status():
    """Display status of all test containers"""
    print_header("Test containers status")
    
    result = run_docker(['ps', '-a', '--filter', 'name=dmm-test-', '--format', 
                        'table {{.Names}}\t{{.Status}}\t{{.Image}}'])
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Colors.RED}Failed to get container status{Colors.ENDC}")
    
    # Also show resource usage
    print(f"\n{Colors.BOLD}Resource usage:{Colors.ENDC}\n")
    stats_result = run_docker(['stats', '--no-stream', '--format',
                              'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}',
                              '--filter', 'name=dmm-test-'])
    
    if stats_result.returncode == 0:
        print(stats_result.stdout)


def main(argv=None):
    """Main entry point"""
    if argv is None:
        argv = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        description='Create test Docker containers for docker-monitor-manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  dmm-test                    # Create all test containers
  dmm-test --cleanup          # Remove all test containers
  dmm-test --status           # Show status of test containers
  dmm-test --cpu --memory     # Create only CPU and memory stress containers
        '''
    )
    
    parser.add_argument('--cleanup', action='store_true',
                       help='Remove all test containers')
    parser.add_argument('--status', action='store_true',
                       help='Show status of test containers')
    parser.add_argument('--cpu', action='store_true',
                       help='Create only CPU stress container')
    parser.add_argument('--memory', action='store_true',
                       help='Create only memory stress container')
    parser.add_argument('--all', action='store_true',
                       help='Create all test containers (default)')
    
    args = parser.parse_args(argv)
    
    # Check if Docker is available
    result = run_docker(['ps'])
    if result.returncode != 0:
        print(f"{Colors.RED}Error: Docker is not running or not accessible{Colors.ENDC}")
        print(f"\nPlease run: {Colors.CYAN}dmm-doctor{Colors.ENDC} to diagnose issues")
        return 1
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}🧪 Docker Monitor Manager - Test Environment{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    # Handle cleanup
    if args.cleanup:
        cleanup_existing_test_containers()
        return 0
    
    # Handle status
    if args.status:
        show_container_status()
        return 0
    
    # Cleanup before creating new containers
    cleanup_existing_test_containers()
    
    # Create containers based on arguments
    if args.cpu:
        create_cpu_stress_container()
    elif args.memory:
        create_memory_stress_container()
    elif args.all or not (args.cpu or args.memory):
        # Create all by default
        create_normal_containers()
        create_cpu_stress_container()
        create_memory_stress_container()
        create_cloneable_containers()
        create_stopped_container()
    
    # Show final status
    time.sleep(2)  # Wait a bit for containers to settle
    show_container_status()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}✓ Test environment ready!{Colors.ENDC}")
    print(f"\n{Colors.CYAN}You can now test docker-monitor-manager with:{Colors.ENDC}")
    print(f"  {Colors.BOLD}dmm{Colors.ENDC}\n")
    print(f"{Colors.CYAN}To cleanup test containers:{Colors.ENDC}")
    print(f"  {Colors.BOLD}dmm-test --cleanup{Colors.ENDC}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
