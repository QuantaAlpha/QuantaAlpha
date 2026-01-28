import importlib.metadata
import platform
import sys
from pathlib import Path

import docker
import requests
from setuptools_scm import get_version

from quantaalpha.log import logger


def sys_info():
    """collect system related info"""
    method_list = [
        ["Name of current operating system: ", "system"],
        ["Processor architecture: ", "machine"],
        ["System, version, and hardware information: ", "platform"],
        ["Version number of the system: ", "version"],
    ]
    for method in method_list:
        logger.info(f"{method[0]}{getattr(platform, method[1])()}")
    return None


def python_info():
    """collect Python related info"""
    python_version = sys.version.replace("\n", " ")
    logger.info(f"Python version: {python_version}")
    return None


def docker_info():
    client = docker.from_env()
    containers = client.containers.list(all=True)
    if containers:
        containers.sort(key=lambda c: c.attrs["Created"])
        last_container = containers[-1]
        logger.info(f"Container ID: {last_container.id}")
        logger.info(f"Container Name: {last_container.name}")
        logger.info(f"Container Status: {last_container.status}")
        logger.info(f"Image ID used by the container: {last_container.image.id}")
        logger.info(f"Image tag used by the container: {last_container.image.tags}")
        logger.info(f"Container port mapping: {last_container.ports}")
        logger.info(f"Container Label: {last_container.labels}")
        logger.info(f"Startup Commands: {' '.join(client.containers.get(last_container.id).attrs['Config']['Cmd'])}")
    else:
        logger.info(f"No run containers.")



def collect_info():
    """Prints information about the system and the installed packages."""
    sys_info()
    python_info()
    docker_info()
    return None
