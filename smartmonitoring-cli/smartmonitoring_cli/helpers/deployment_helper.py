import logging as lg
from smartmonitoring_cli.handlers.data_handler import DataHandler
from smartmonitoring_cli.handlers.docker_handler import DockerHandler, ContainerCreateError, \
    ImageDoesNotExist
from smartmonitoring_cli.models.local_config import LocalConfig
from smartmonitoring_cli.models.update_manifest import UpdateManifest


def replace_deployment(current_config: LocalConfig,
                       new_config: LocalConfig,
                       current_manifest: UpdateManifest,
                       new_manifest: UpdateManifest,
                       cfh: DataHandler,
                       dock: DockerHandler) -> bool:
    """
    Replaces the currently running containers with new ones
    :param current_config: LocalConfig object of the currently running containers
    :param new_config: LocalConfig object for the new containers
    :param current_manifest: UpdateManifest object of the currently running containers
    :param new_manifest: UpdateManifest object for the new containers
    :param cfh: DataHandler instance
    :param dock: DockerHandler instance
    :return: True if successful, False otherwise
    """
    cfh.validate_config_against_manifest(new_config, new_manifest)
    cfh.save_status("Deploying")
    try:
        dock.pull_images(new_manifest.containers)
    except ImageDoesNotExist as e:
        cfh.save_status(status="DeploymentError", error_msg=str(e))
        dock.perform_cleanup()
        raise

    try:
        uninstall_application(current_manifest, dock)
        lg.info("Creating new containers...")
        install_deployment(new_config, new_manifest, dock, cfh)
    except ContainerCreateError as e:
        __perform_fallback(cfh, current_config, current_manifest, dock, e, new_manifest)
        return False
    else:
        cfh.save_installed_stack(new_config, new_manifest)
        cfh.save_status("Deployed", upd_channel=new_config.update_channel,
                        pkg_version=new_manifest.package_version)
        lg.info("Performing cleanup...")
        dock.perform_cleanup()
        lg.info("Containers successfully deployed")
    return True


def __perform_fallback(cfh: DataHandler, current_config: LocalConfig, current_manifest: UpdateManifest,
                       dock: DockerHandler, e: Exception, new_manifest: UpdateManifest) -> None:
    """
    Performs a fallback to the previous deployment
    :param cfh: DataHandler instance
    :param current_config: LocalConfig object of the currently running containers
    :param current_manifest: UpdateManifest object of the currently running containers
    :param dock: DockerHandler instance
    :param e: Exception that was raised
    :param new_manifest: UpdateManifest object that was attempted to be deployed
    """
    lg.error(f"Error while deploying new containers: {e}")
    lg.info("Performing fallback to previous version...")
    lg.debug("Removing possibly created new containers")
    uninstall_application(new_manifest, dock)
    lg.info("Creating old containers...")
    install_deployment(current_config, current_manifest, dock, cfh)
    cfh.save_status("DeploymentError", error_msg=str(e))
    lg.info("Performing cleanup...")
    dock.perform_cleanup()
    lg.info("Old containers successfully created")


def install_deployment(config: LocalConfig,
                       manifest: UpdateManifest,
                       dock: DockerHandler,
                       cfh: DataHandler) -> None:
    """
    Creates the containers for the given config and manifest
    :param config: LocalConfig object
    :param manifest: UpdateManifest object
    :param dock: DockerHandler instance
    :param cfh: DataHandler instance
    """
    env_secrets = cfh.generate_dynamic_secrets(manifest.dynamic_secrets)
    for container in manifest.containers:
        env_vars = cfh.compose_env_variables(config, container, env_secrets)
        lg.info(f"Deploying container: {container.name} with image: {container.image}")

        # Set local file path based on config file
        if container.files is not None:
            container_files = cfh.compose_mapped_files(container, config)
            dock.create_container(container, env_vars, container_files)
        else:
            dock.create_container(container, env_vars)
    dock.start_containers(manifest.containers)
    pass


def uninstall_application(manifest: UpdateManifest, dock: DockerHandler) -> None:
    """
    Removes the containers for the given manifest
    :param manifest: Current UpdateManifest object
    :param dock: DockerHandler instance
    """
    lg.info("Decommission currently running containers...")
    dock.remove_containers(manifest.containers)
    pass
