import logging as lg
import time
from typing import Optional

import docker
from docker import errors
from docker.errors import NotFound, APIError
from docker.models import containers
from docker.types import Mount, LogConfig

from smartmonitoring_cli.models.update_manifest import ContainerConfig, MappedFile, Port


class DockerInstanceUnavailable(Exception):
    pass


class ContainerCreateError(Exception):
    pass


class ImageDoesNotExist(Exception):
    pass


class DockerHandler:
    def __init__(self, client: docker = None):
        if client is None:
            self.__connect_to_local_docker_instance()

    def __connect_to_local_docker_instance(self, attempt: int = 1) -> None:
        """
        Connect to the local docker instance
        :param attempt: Amount of attempts to connect to the docker instance
        before a DockerInstanceUnavailable exception is raised
        """
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
        """
        Get a container by its name
        :param container_name: Name of the container as string
        :return: Docker container object
        """
        try:
            lg.debug(f'Getting container {container_name}')
            return self.client.containers.get(container_name)
        except NotFound:
            lg.debug("Container " + container_name + " not found")
            raise

    def get_containers_from_config(self, conf_containers: list[ContainerConfig]) -> list[containers.Container]:
        """
        Get a list of Docker container objects from a list of ContainerConfig objects
        :param conf_containers: List of ContainerConfig objects
        :return: List of Docker container objects
        """
        containers = []
        for container in conf_containers:
            containers.append(self.get_container(container.name))
        return containers

    def get_container_stats(self, container_config: ContainerConfig) -> dict:
        """
        Get statistics of a container (status, cpu usage, memory usage ...)
        :param container_config: ContainerConfig object
        :return: Dict with statistics of the container
        """
        container = None
        try:
            container = self.get_container(container_config.name)
            name = container.name
            status = container.status
            image = container_config.image
        except NotFound:
            name = container_config.name
            status = "Not found"
            image = "-"
            mem_usage_mb = "-"
            mem_usage_percent = "-"

        if container is not None:
            try:
                stats = container.stats(decode=False, stream=False)
                mem_usage_mb = str(round(stats['memory_stats']['usage'] / 1024 / 1024, 2)) + " MB"
                mem_usage_percent = str(self.__calculate_cpu_usage(stats)) + " %"
            except KeyError as e:
                lg.debug(f'Error getting statistics for Container {container.name} {e}')
                mem_usage_mb = "N/A"
                mem_usage_percent = "N/A"

        return {
            'name': name,
            'status': status,
            'image': image,
            "mem_usg_mb": mem_usage_mb,
            "cpu_usg_present": mem_usage_percent
        }

    def __calculate_cpu_usage(self, stats: dict) -> float:
        """
        Calculate the cpu usage of a container based on the stats form docker api
        :param stats: Stats dict of a container
        :return: CPU usage as float
        """
        usage_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        len_cpu = stats['cpu_stats']['online_cpus']
        percentage = (usage_delta / system_delta) * len_cpu * 100
        return round(percentage, 2)

    def start_container(self, container_name: str) -> None:
        """
        Start a container by its name
        :param container_name: Name of the container as string
        """
        try:
            lg.info(f'Starting Container {container_name}')
            container = self.get_container(container_name)
            container.start()
            lg.debug(f'Container {container_name} started')
        except APIError as e:
            lg.critical(f'Error stopping container: {container_name}')
            raise e

    def stop_container(self, container_name: str):
        """
        Stop a container by its name
        :param container_name: Name of the container as string
        """
        try:
            container = self.get_container(container_name)
            lg.info(f'Stopping container {container_name}')
            container.stop()
            lg.debug(f'Container {container_name} stopped')
        except NotFound:
            lg.info(f'Skip stopping container {container_name} because it does not exist')
        except APIError:
            lg.error(f'Error stopping container: {container_name}')
            raise

    def restart_container(self, container_name: str) -> None:
        """
        Restart a container by its name
        :param container_name: Name of the container as string
        """
        try:
            lg.info(f'Restarting container {container_name}')
            container = self.get_container(container_name)
            container.restart()
            lg.debug(f'Container {container_name} restarted')
        except APIError:
            lg.error(f'Error restarting container: {container_name}')
            raise

    def restart_containers(self, conf_containers: list[ContainerConfig]) -> None:
        """
        Restart a list of containers
        :param conf_containers: List of ContainerConfig objects
        """
        for container in conf_containers:
            self.restart_container(container.name)

    def stop_containers(self, conf_containers: list[ContainerConfig]) -> None:
        """
        Stop a list of containers
        :param conf_containers: List of ContainerConfig objects
        """
        for container in conf_containers:
            self.stop_container(container.name)

    def start_containers(self, conf_containers: list[ContainerConfig]) -> None:
        """
        Start a list of containers
        :param conf_containers: List of ContainerConfig objects
        """
        for container in conf_containers:
            self.start_container(container.name)

    def remove_containers(self, conf_containers: list[ContainerConfig]) -> None:
        """
        Remove a list of containers
        :param conf_containers: List of ContainerConfig objects
        """
        self.stop_containers(conf_containers)
        for container in conf_containers:
            self.remove_container(container.name)

    def remove_container(self, container_name: str) -> None:
        """
        Remove a container by its name
        :param container_name: Name of the container as string
        """
        try:
            container = self.get_container(container_name)
            lg.info(f'Removing container {container_name}')
            container.remove(force=True)
        except NotFound:
            lg.debug(f'Skipping removal of container {container_name} because it does not exist')

    def create_inter_network(self) -> None:
        """
        Create the smartmonitoring bridge network
        """
        try:
            self.client.networks.get('smartmonitoring_cli')
            lg.debug("SmartMonitoring bridge network already exists")
        except NotFound:
            self.client.networks.create(
                "smartmonitoring_cli", driver="bridge", check_duplicate=True, internal=True)
            lg.info(
                "SmartMonitoring bridge network for container communication created")

    def remove_inter_network(self) -> None:
        """
        Remove the smartmonitoring bridge network
        """
        try:
            self.client.networks.get('smartmonitoring_cli').remove()
            lg.info("SmartMonitoring bridge network removed")
        except NotFound:
            lg.debug("SmartMonitoring bridge network not found, skipping removal")

    def __connect_container_to_inter_network(self, container: containers.Container) -> None:
        """
        Connect a container to the smartmonitoring bridge network
        :param container: Docker container object to connect
        """
        network = self.client.networks.get("smartmonitoring_cli")
        network.connect(container)
        lg.debug(f'Container {container.name} connected to SmartMonitoring bridge network')

    def perform_cleanup(self) -> None:
        """
        Perform a cleanup of all unused images and volumes
        """
        self.__remove_unused_images()
        self.__remove_unused_volumes()

    def __remove_unused_images(self) -> None:
        """
        Remove all unused images
        """
        images = self.client.images.prune(filters={'dangling': False})
        if images["ImagesDeleted"] is None: return
        lg.debug(f'Removed {len(images["ImagesDeleted"])} images and freed {images["SpaceReclaimed"]} bytes')

    def __remove_unused_volumes(self) -> None:
        """
        Remove all unused volumes
        """
        volumes = self.client.volumes.prune()
        if volumes["VolumesDeleted"] is None: return
        lg.debug(f'Removed {len(volumes["VolumesDeleted"])} volumes and freed {volumes["SpaceReclaimed"]} bytes')

    def __check_if_image_exists(self, image_name: str) -> bool:
        """
        Check if an image exists in local docker instance
        :param image_name: Name of the image as string
        :return: True if image exists, False otherwise
        """
        try:
            image = self.client.images.get(image_name)
            lg.debug(f'Image {image} exists')
            return True
        except NotFound:
            lg.debug(f'Image {image_name} does not exist in local docker instance')
            return False

    def pull_images(self, containers_config: list[ContainerConfig]) -> None:
        """
        Pull all images for a list of containers. If an image is not found on Docker Hub, a ImageDoesNotExist exception
        is raised
        :param containers_config: List of ContainerConfig objects
        """
        exist = True
        not_found_images = []
        for container in containers_config:
            if not self.__check_if_image_exists(container.image):
                try:
                    self.__pull_image_if_not_exists(container.image)
                except ImageDoesNotExist:
                    not_found_images.append(container.image)
                    exist = False
        if not exist:
            raise ImageDoesNotExist(f'Error pulling the following images from Docker hub: {not_found_images}')

    def __pull_image_if_not_exists(self, image: str) -> None:
        """
        Pull an image from Docker Hub if it does not exist in local docker instance
        :param image: Name of the image as string
        """
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
        """
        Compose a list of Mount objects from a list of MappedFile objects
        :param files: List of MappedFile objects to compose
        :return: List of Docker Mount objects
        """
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
        """
        Compose a dictionary of ports from a list of Port objects
        :param ports: List of Port objects to compose
        :return: dictionary of ports
        """
        if ports is None: return None
        port_bindings = {}
        lg.debug(f'Composing ports {ports} to docker port mapping dict')
        for port in ports:
            port_bindings[f'{port.container_port}/{port.protocol}'] = port.host_port
        lg.debug(f'Docker port bindings objects created: {port_bindings}')
        return port_bindings

    def __create_container_logger(self, container_name: str) -> LogConfig:
        """
        Create a LogConfig object for a container
        :param container_name: Name of the container, used for the name of the log file
        :return: LogConfig object
        """
        return LogConfig(type=LogConfig.types.JSON, config={
            'max-size': '500m',
            'labels': f'{container_name}_log'
        })

    def create_container(self, container: ContainerConfig, env_vars: dict, files: list[MappedFile] = None) -> None:
        """
        Create a container from a ContainerConfig object
        :param container: ContainerConfig object
        :param env_vars: Environment variables to pass to the container
        :param files: List of MappedFile objects to mount in the container
        """
        self.remove_container(container.name)
        try:
            mapped_files = self.__compose_files(files)
            mapped_ports = self.__compose_ports(container.ports)
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
                log_config=self.__create_container_logger(container.name),
                restart_policy={"Name": "unless-stopped"},
                privileged=container.privileged,
                detach=True)
            self.__connect_container_to_inter_network(container)
        except (APIError, ImageDoesNotExist) as e:
            lg.error(f'Error creating container {container.name}')
            raise ContainerCreateError(e) from e
