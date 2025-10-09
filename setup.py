#!/usr/bin/env python3
"""
Docker Monitor - A powerful desktop tool for monitoring and managing Docker containers.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
def read_readme():
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        return f.read()

# Read requirements
def read_requirements():
    here = os.path.abspath(os.path.dirname(__file__))
    requirements_path = os.path.join(here, 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return ['docker']

setup(
    name="docker-monitor-manager",
    version="1.0.3",
    
    # Package information
    description="A powerful desktop tool for monitoring and managing Docker containers",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="Amir Khoshdel Louyeh",
    author_email="amirkhoshdellouyeh@gmail.com",  # Replace with your actual email
    
    # Repository information
    url="https://github.com/amir-khoshdel-louyeh/docker-monitor-manager",
    
    # Package structure
    packages=find_packages(),
    include_package_data=True,
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Entry point for command-line usage
    entry_points={
        "console_scripts": [
            "docker-monitor-manager=docker_monitor.main:main",
            "dmm=docker_monitor.main:main",
            "dmm-config=docker_monitor.config_cli:main",
        ],
    },
    
    # Classifiers help users find your project
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
        "Topic :: System :: Monitoring",
    ],
    
    # Additional metadata
    keywords="docker monitoring containers gui desktop management docker-containers system-monitoring",
    
    # License
    license="MIT",
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/amir-khoshdel-louyeh/docker-monitor-manager/issues",
        "Source": "https://github.com/amir-khoshdel-louyeh/docker-monitor-manager",
        "Documentation": "https://github.com/amir-khoshdel-louyeh/docker-monitor-manager#readme",
    },
)