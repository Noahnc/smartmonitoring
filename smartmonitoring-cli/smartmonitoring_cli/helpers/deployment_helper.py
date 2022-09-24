import logging as lg
from smartmonitoring_cli.handlers.data_handler import DataHandler
from smartmonitoring_cli.handlers.docker_handler import DockerHandler, ContainerCreateError, \
    ImageDoesNotExist
from smartmonitoring_cli.models.local_config import LocalConfig
from smartmonitoring_cli.models.update_manifest import UpdateManifest, ContainerConfig


def replace_deployment(current_config: LocalConfig,
                         new_config: LocalConfig,
                         current_manifest: UpdateManifest,
                         new_manifest: UpdateManifest,
                         cfh: DataHandler,
                         dock: DockerHandler) -> bool:

    cfh.validate_config_against_manifest(new_config, new_manifest)
    cfh.save_status("Deploying")
    try:
        dock.pull_images(new_manifest.containers)
    except ImageDoesNotExist as e:
        cfh.save_status(status="DeploymentError", error_msg=str(e))
        dock.perform_cleanup()
        raise

    try:
        lg.info("Removing old containers...")
        uninstall_application(current_manifest, dock)
        lg.info("Creating new containers...")
        install_application(new_config, new_manifest, dock, cfh)
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


def __perform_fallback(cfh, current_config, current_manifest, dock, e, new_manifest):
    lg.error(f"Error while deploying new containers: {e}")
    lg.info("Performing fallback to previous version...")
    lg.debug("Removing possibly created new containers...")
    uninstall_application(new_manifest, dock)
    lg.info("Creating old containers...")
    install_application(current_config, current_manifest, dock)
    cfh.save_status("DeploymentError", error_msg=str(e))
    lg.info("Performing cleanup...")
    dock.perform_cleanup()
    lg.info("Old containers successfully created...")


def install_application(config: LocalConfig,
                          manifest: UpdateManifest,
                          dock: DockerHandler,
                          cfh: DataHandler) -> None:
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
    lg.info("Decommission currently running containers...")
    dock.remove_containers(manifest.containers)
    pass