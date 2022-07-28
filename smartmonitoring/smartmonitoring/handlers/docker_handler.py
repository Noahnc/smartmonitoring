import logging as lg

import time
from typing import Optional

import docker
from docker import errors
from docker.errors import NotFound, APIError
from docker.models import containers

from docker.types import Mount

from smartmonitoring.models.update_manifest import ContainerConfig, MappedFile, Port


class DockerInstanceUnavailable(Exception):
    pass


class ContainerCreateError(Exception):
    pass


class ImageDoesNotExist(Exception):
    pass


class DockerHandler:
    def __init__(self):
        self.__connect_to_local_docker_instance()

    def __connect_to_local_docker_instance(self, attempt: int = 1) -> None:
        retries = 3
        if attempt > retries:
            lg.error("Could not connect to local docker instance")
            raise DockerInstanceUnavailable("Could not connect to local docker instance")
        try:
            self.client = docker.from_env()
        except errors.DockerException as e:
            lg.warning(f'Error connecting to local docker instance, attempt {attempt} of {retries}, retry in 10s.')
            lg.debug(f'Message: {e}')
            time.sleep(10)
            self.__connect_to_local_docker_instance(attempt + 1)

    def get_container(self, container_name: str) -> containers.Container:
        try:
            lg.debug(f'Getting container {container_name}')
            return self.client.containers.get(container_name)
        except NotFound:
            lg.debug("Container " + container_name + " not found")
            raise

    def get_container_stats(self, container: containers.Container) -> dict:
        stats = container.stats(decode=False, stream=False)
        try:
            statistics = {
                "mem_usg_mb": round(stats['memory_stats']['usage'] / 1024 / 1024, 2),
                "cpu_usg_present": self.__calculate_cpu_usage(stats)
            }
        except KeyError as e:
            lg.warning(f'Error getting statistics for Container {container.name} {e}')
            statistics = {
                "mem_usg_mb": "N/A",
                "cpu_usg_present": "N/A"
            }
        return statistics

    def __calculate_cpu_usage(self, stats: dict) -> float:
        usage_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        len_cpu = stats['cpu_stats']['online_cpus']
        percentage = (usage_delta / system_delta) * len_cpu * 100
        return round(percentage, 2)

    def start_container(self, container_name: str) -> None:
        try:
            lg.info(f'Starting Container {container_name}')
            container = self.get_container(container_name)
            container.start()
            lg.debug(f'Container {container_name} started')
        except APIError as e:
            lg.critical(f'Error stopping container: {container_name}')
            raise e

    def stop_container(self, container_name: str):
        try:
            lg.info(f'Stopping container {container_name}')
            container = self.get_container(container_name)
            container.stop()
            lg.debug(f'Container {container_name} stopped')
        except NotFound:
            lg.info(f'Skip stopping container {container_name} because it does not exist')
        except APIError:
            lg.error(f'Error stopping container: {container_name}')
            raise

    def restart_container(self, container_name: str) -> None:
        try:
            lg.info(f'Restarting container {container_name}')
            container = self.get_container(container_name)
            container.restart()
            lg.debug(f'Container {container_name} restarted')
        except APIError as e:
            lg.error(f'Error restarting container: {container_name}')
            raise

    def restart_containers(self, conf_containers: list[ContainerConfig]) -> None:
        for container in conf_containers:
            self.restart_container(container.name)

    def stop_containers(self, conf_containers: list[ContainerConfig]) -> None:
        for container in conf_containers:
            self.stop_container(container.name)

    def start_containers(self, conf_containers: list[ContainerConfig]) -> None:
        for container in conf_containers:
            self.start_container(container.name)

    def remove_containers(self, conf_containers: list[ContainerConfig]) -> None:
        self.stop_containers(conf_containers)
        for container in conf_containers:
            self.remove_container(container.name)

    def remove_container(self, container_name: str) -> None:
        try:
            container = self.get_container(container_name)
            lg.info(f'Removing container {container_name}')
            container.remove(force=True)
        except NotFound as e:
            lg.debug(f'Skipping removal of container {container_name} because it does not exist')

    def create_inter_network(self) -> None:
        try:
            self.client.networks.get('smartmonitoring')
            lg.debug("SmartMonitoring bridge network already exists")
        except NotFound as e:
            self.client.networks.create(
                "smartmonitoring", driver="bridge", check_duplicate=True, internal=True)
            lg.info(
                "SmartMonitoring bridge network for container communication created")

    def remove_inter_network(self) -> None:
        try:
            self.client.networks.get('smartmonitoring').remove()
            lg.info("SmartMonitoring bridge network removed")
        except NotFound as e:
            lg.debug("SmartMonitoring bridge network not found, skipping removal")

    def __connect_container_to_inter_network(self, container: containers.Container) -> None:
        network = self.client.networks.get("smartmonitoring")
        network.connect(container)
        lg.debug(f'Container {container.name} connected to SmartMonitoring bridge network')

    def perform_cleanup(self) -> None:
        self.__remove_unused_images()
        self.__remove_unused_volumes()

    def __remove_unused_images(self) -> None:
        images = self.client.images.prune(filters={'dangling': False})
        if images["ImagesDeleted"] is None: return
        lg.debug(f'Removed {len(images["ImagesDeleted"])} images and freed {images["SpaceReclaimed"]} bytes')

    def __remove_unused_volumes(self) -> None:
        volumes = self.client.volumes.prune()
        if volumes["VolumesDeleted"] is None: return
        lg.debug(f'Removed {len(volumes["VolumesDeleted"])} volumes and freed {volumes["SpaceReclaimed"]} bytes')

    def __check_if_image_exists(self, image_name: str) -> bool:
        try:
            image = self.client.images.get(image_name)
            return True
        except NotFound as e:
            lg.debug(f'Image {image_name} does not exist in local docker instance')
            return False

    def __pull_image_if_not_exists(self, image: str) -> None:
        if not self.__check_if_image_exists(image):
            try:
                lg.info(f'Pulling image {image} from docker hub')
                self.client.images.pull(image)
                lg.debug(f'Image {image} pulled from docker hub')
            except APIError as e:
                lg.error(f'Error pulling image {image}')
                raise ImageDoesNotExist(e)
        else:
            lg.debug(f'Image {image} already exists, skip pulling')

    def __compose_files(self, files: list[MappedFile]) -> Optional[list[Mount]]:
        if files is None: return None
        mount_files = []
        lg.debug(f'Composing files {files} to docker mounts object')
        for file in files:
            mount_files.append(Mount(
                source=file.host_path,
                target=file.container_path,
                type='bind'))
        lg.debug(f'Docker mounts objects created: {mount_files}')
        return mount_files

    def __compose_ports(self, ports: list[Port]) -> Optional[dict]:
        if ports is None: return None
        port_bindings = {}
        lg.debug(f'Composing ports {ports} to docker port mapping dict')
        for port in ports:
            port_bindings[f'{port.container_port}/{port.protocol}'] = port.host_port
        lg.debug(f'Docker port bindings objects created: {port_bindings}')
        return port_bindings

    def create_container(self, container: ContainerConfig, env_vars: dict, files: list[MappedFile] = None) -> None:
        self.remove_container(container.name)
        try:
            mapped_files = self.__compose_files(files)
            mapped_ports = self.__compose_ports(container.ports)
            self.__pull_image_if_not_exists(container.image)
            lg.debug(
                f'Creating container {container.name} with image {container.image}, hostname {container.hostname} and '
                f'env {env_vars}')
            container = self.client.containers.create(
                container.image,
                name=container.name,
                environment=env_vars,
                hostname=container.hostname,
                mounts=mapped_files,
                ports=mapped_ports,
                restart_policy={"Name": "unless-stopped"},
                privileged=container.privileged,
                detach=True)
            self.__connect_container_to_inter_network(container)
        except APIError or ImageDoesNotExist as e:
            lg.error(f'Error creating container {container.name}')
            raise ContainerCreateError(e) from e



