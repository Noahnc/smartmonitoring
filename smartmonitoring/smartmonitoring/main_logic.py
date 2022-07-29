import logging as lg
import os
import socket
import sys
import time
from pathlib import Path

from packaging import version
from rich.console import Console
from rich.live import Live
from rich.table import Table

import smartmonitoring.const_settings as cs
import smartmonitoring.helpers.cli_helper as cli
import smartmonitoring.helpers.helper_functions as hf
import smartmonitoring.helpers.log_helpers as lh
from smartmonitoring import __version__
from smartmonitoring.handlers.data_handler import ConfigError, ManifestError, \
    ValueNotFoundInConfig, InstalledStackInvalid
from smartmonitoring.handlers.data_handler import DataHandler
from smartmonitoring.handlers.docker_handler import DockerHandler, DockerInstanceUnavailable
from smartmonitoring.models.local_config import LocalConfig
from smartmonitoring.models.update_manifest import UpdateManifest, ContainerConfig

PARENT_FOLDER = os.path.dirname(os.path.dirname(__file__))


class MainLogic:
    def __init__(self):
        if sys.platform.startswith("linux"):
            self.smartmonitoring_config_dir = Path("/etc/smartmonitoring")
            self.smartmonitoring_log_dir = Path("/var/log/smartmonitoring")
            self.smartmonitoring_var_dir = Path("/var/smartmonitoring")
        else:
            self.smartmonitoring_config_dir = os.path.join(PARENT_FOLDER, "config_files")
            self.smartmonitoring_log_dir = os.path.join(PARENT_FOLDER, "logs")
            self.smartmonitoring_var_dir = os.path.join(PARENT_FOLDER, "temp")

            hf.create_folder_if_not_exists(self.smartmonitoring_log_dir)
            hf.create_folder_if_not_exists(self.smartmonitoring_var_dir)
        self.stack_file = Path(os.path.join(self.smartmonitoring_var_dir, cs.DEPLOYED_STACK_FILE_NAME))
        self.status_file = Path(os.path.join(self.smartmonitoring_var_dir, cs.STATUS_FILE_NAME))
        self.config_file = Path(os.path.join(self.smartmonitoring_config_dir, cs.LOCAL_CONF_FILE_NAME))

        self.cfh = DataHandler(self.config_file, self.stack_file, self.status_file)
        pass

    def setup_logging(self, debug: bool, silent: bool) -> None:
        log_file_path = os.path.join(self.smartmonitoring_log_dir, cs.LOG_FILE_NAME)
        if debug and silent:
            lh.setup_file_logger(file=log_file_path)
            return
        elif not silent:
            lh.add_console_logger(debug)
            return
        lh.setup_file_logger(file=log_file_path, level="INFO")
        if self.__check_if_deployed():
            try:
                config, manifest = self.cfh.get_installed_stack()
            except InstalledStackInvalid as e:
                lg.critical(f'Error loading Config to update file logger: {e}')
                lh.update_file_logger(level="DEBUG")
                return
            if config.debug_logging:
                lh.update_file_logger(level="DEBUG", size=config.log_file_size_mb, count=config.log_file_count)
            else:
                lh.update_file_logger(size=config.log_file_size_mb, count=config.log_file_count)
        else:
            lh.update_file_logger(level="DEBUG")
            return

    def check_configurations(self, debug: bool) -> None:
        config_valid = True
        config_message = "Local Config is valid"
        manifest_valid = True
        manifest_message = "Manifest is valid"
        try:
            self.cfh.get_configs()
            lg.info("Configuration and manifest are valid!")
        except ConfigError as e:
            config_valid = False
            config_message = e
            manifest_valid = "-"
            manifest_message = "Skipped because of error with local config file"
            if debug: raise e
        except ManifestError as e:
            manifest_valid = False
            manifest_message = e
            if debug: raise e
        except ValueNotFoundInConfig as e:
            config_valid = False
            config_message = e
            manifest_valid = False
            manifest_message = e
            if debug: raise e
        if debug: return
        cli.print_logo()
        table = Table(width=cs.CLI_WIDTH,
                      title="Configuration and Manifest Validation")
        table.add_column("Config File", justify="center", width=cs.CLI_WIDTH)
        table.add_column("Update Manifest", justify="center", width=cs.CLI_WIDTH)
        table.add_row("[blue]Valid", "[blue]Valid")
        table.add_row(f'[green]{config_valid}' if config_valid else f'[red]{config_valid}',
                      f'[green]{manifest_valid}' if manifest_valid else f'[red]{manifest_valid}')
        table.add_row()
        table.add_row("[blue]Message", "[blue]Message")
        table.add_row(f'[green]{config_message}' if config_valid else f'[red]{config_message}',
                      f'[green]{manifest_message}' if manifest_valid else f'[green]{manifest_message}')
        table.add_row()

        Console().print(table)

    def validate_and_apply_config(self, silent: bool) -> None:
        if not self.__check_if_deployed():
            lg.warning(
                "SmartMonitoring is not deployed on this system. Before you can apply a new configuration, "
                "you have to deploy the application...")
            return
        if self.check_if_deployment_in_progress():
            lg.warning("Deployment is already in progress. Please wait until it is finished.")
            return
        current_config, manifest = self.cfh.get_installed_stack()
        try:
            lg.info("Validating new local configuration...")
            new_config = self.cfh.get_local_config()
            self.cfh.validate_config_against_manifest(new_config, manifest)
        except ConfigError or ValueNotFoundInConfig as e:
            lg.error(f'Config file is invalid: {e}')
            lg.info("You can validate the config file by running 'smartmonitoring validate-config'")
            return
        lg.info("Config file is valid")
        identical, changes = self.cfh.compare_local_config(current_config, new_config)
        if identical:
            lg.warning("No changes found in local config, nothing to apply...")
            return
        if not silent and not cli.print_and_confirm_changes(changes):
            lg.info("Skipped applying new configuration...")
            return
        lg.info("Applying new local configuration...")
        self.__replace_deployment(current_config, new_config, manifest, manifest)

    def print_status(self, disable_refresh) -> None:
        cli.print_logo()
        if self.__check_if_deployed():
            config, manifest = self.cfh.get_installed_stack()
            self.__print_system_status(config, manifest)
            self.__print_container_status(disable_refresh, manifest.containers)
        else:
            self.__print_system_status()
            self.__print_container_status(disable_refresh)

    def restart_application(self) -> None:
        if not self.__check_if_deployed():
            lg.warning("SmartMonitoring is not deployed, skipping restart...")
            return
        if self.check_if_deployment_in_progress():
            lg.warning("Deployment is in progress. Please wait until it is finished.")
            return

        lg.info("Restarting smartmonitoring application...")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        dock.restart_containers(manifest.containers)
        lg.info("All containers restarted successfully...")

    def deploy_application(self) -> None:
        if self.__check_if_deployed():
            lg.warning("SmartMonitoring is already deployed, skipping deployment...")
            return
        lg.info("Deploying smartmonitoring application to this system...")
        lg.info("Retrieving local configuration and update manifest...")
        config, manifest = self.cfh.get_configs()
        dock = DockerHandler()
        self.cfh.save_status("Deploying")
        dock.create_inter_network()
        self.__install_application(config, manifest, dock)
        self.cfh.save_installed_stack(config, manifest)
        self.cfh.save_status("Deployed", upd_channel=config.update_channel, pkg_version=manifest.package_version)
        lg.info("SmartMonitoring application successfully deployed...")

    def remove_application(self) -> None:
        if not self.__check_if_deployed():
            lg.warning("SmartMonitoring is not deployed, skipping removal...")
            return
        if self.check_if_deployment_in_progress():
            lg.warning("Deployment is in progress. Please wait until it is finished.")
            return
        lg.info("Removing smartmonitoring deployment from this system...")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        self.__uninstall_application(manifest, dock)
        dock.remove_inter_network()
        dock.perform_cleanup()
        self.cfh.remove_var_data_files()
        lg.info("SmartMonitoring application successfully removed...")

    def update_application(self, force: bool) -> None:
        if not self.__check_if_deployed():
            lg.warning("SmartMonitoring is not deployed on this system. Please deploy SmartMonitoring first.")
            return
        if self.check_if_deployment_in_progress():
            lg.warning("Deployment is already in progress. Please wait until it is finished.")
            return
        lg.info("Updating smartmonitoring application to this system...")
        lg.info("Retrieving local configuration and update manifest...")
        config, current_manifest = self.cfh.get_installed_stack()
        new_manifest = self.cfh.get_update_manifest(config)
        if not force and not self.__check_version_is_newer(current_manifest.package_version,
                                                           new_manifest.package_version):
            lg.warning("No newer version of smartmonitoring is available, skipping update...")
            return
        if force or self.__check_version_is_newer(current_manifest.package_version, new_manifest.package_version):
            lg.info(
                f"Update SmartMonitoring from {current_manifest.package_version} to {new_manifest.package_version}...")
            self.__replace_deployment(config, config, current_manifest, new_manifest)
            lg.info(f"SmartMonitoring successfully updated to version {new_manifest.package_version}...")

    def __replace_deployment(self, current_config: LocalConfig, new_config: LocalConfig,
                             current_manifest: UpdateManifest, new_manifest: UpdateManifest) -> None:
        dock = DockerHandler()
        self.cfh.validate_config_against_manifest(new_config, new_manifest)
        lg.info("Removing old containers...")
        self.__uninstall_application(current_manifest, dock)
        try:
            lg.info("Creating new containers...")
            self.__install_application(new_config, new_manifest, dock)
        except Exception as e:
            lg.error(f"Error while deploying new containers: {e}")
            lg.info("Performing fallback to previous version...")
            lg.debug("Removing possibly created new containers...")
            self.__uninstall_application(new_manifest, dock)
            lg.info("Creating old containers...")
            self.__install_application(current_config, current_manifest, dock)
            self.cfh.save_status("UpdateError", error_msg=str(e))
        else:
            self.cfh.save_installed_stack(new_config, new_manifest)
            self.cfh.save_status("Deployed", upd_channel=new_config.update_channel,
                                 pkg_version=new_manifest.package_version)
            dock.perform_cleanup()
            lg.info("New containers successfully deployed...")

    def __install_application(self, config: LocalConfig, manifest: UpdateManifest, dock: DockerHandler) -> None:
        env_secrets = self.cfh.generate_dynamic_secrets(manifest.dynamic_secrets)
        for container in manifest.containers:
            env_vars = self.cfh.compose_env_variables(config, container, env_secrets)
            lg.info(
                f"Deploying container: {container.name} with image: {container.image}")

            # Set local file path based on config file
            if container.files is not None:
                container_files = self.cfh.compose_mapped_files(container, config)
                dock.create_container(container, env_vars, container_files)
            else:
                dock.create_container(container, env_vars)
        dock.start_containers(manifest.containers)
        pass

    def __uninstall_application(self, manifest: UpdateManifest, dock: DockerHandler) -> None:
        lg.info("Decommission currently running containers...")
        dock.remove_containers(manifest.containers)
        pass

    def __check_version_is_newer(self, current_version: str, new_version: str) -> bool:
        if version.parse(current_version) < version.parse(new_version):
            lg.debug(f"Current version: {current_version} is older than new version: {new_version}")
            return True
        elif version.parse(current_version) == version.parse(new_version):
            lg.debug(f"Current version: {current_version} is the same as the update manifests version: {new_version}")
            return False
        else:
            lg.debug(
                f"Current version: {current_version} is newer than the the update manifests version: {new_version}")
            return False

    def __check_if_deployed(self) -> bool:
        lg.debug("Checking if smartmonitoring application is already deployed...")
        if self.stack_file.exists():
            lg.debug("SmartMonitoring application is deployed on this system...")
            return True
        else:
            lg.debug("SmartMonitoring application is not deployed on this system...")
            return False

    def check_if_deployment_in_progress(self) -> bool:
        if not self.status_file.exists():
            lg.debug("No deployment in progress...")
            return False
        data = self.cfh.get_status()
        if data["status"] == "Deploying":
            lg.debug("Deployment already in progress...")
            return True
        else:
            lg.debug("No deployment in progress...")
            return False

    def __print_system_status(self, config: LocalConfig = None, manifest: UpdateManifest = None) -> None:
        if config is None or manifest is None:
            status = "Not deployed"
            version = "-"
            channel = "-"
            proxy_name = "-"
        else:
            status = self.cfh.get_status()["status"]
            version = manifest.package_version
            channel = config.update_channel
            proxy_name = config.zabbix_proxy_container.proxy_name
        table = Table(width=cs.CLI_WIDTH,
                      title="System and Deployment Status",
                      show_header=False)
        table.add_column("Host Information", justify="center", width=cs.CLI_WIDTH)
        table.add_column("Deployment Status", justify="center", width=cs.CLI_WIDTH)
        table.add_row("[blue]Hostname", "[blue]Status")
        table.add_row(socket.gethostname(), "[green]Deployed" if status == "Deployed" else "[red]Not deployed")
        table.add_row()
        table.add_row("[blue]Updater Version", "[blue]Version")
        table.add_row(__version__, version)
        table.add_row()
        table.add_row("[blue]Local IP Address", "[blue]Update Channel")
        table.add_row(socket.gethostbyname(socket.gethostname()), channel)
        table.add_row()
        table.add_row("[blue]Public IP Address", "[blue]Proxy Name")
        table.add_row(hf.get_public_ip_address(), proxy_name)

        Console().print(table)

    def __generate_container_table(self, containers: list[ContainerConfig], dock: DockerHandler,
                                   initializing: bool) -> Table:
        grid = Table.grid()
        table = Table(width=cs.CLI_WIDTH, title="Container Statistics")
        grid.add_column()
        grid.add_row(table)
        if initializing:
            table.add_column("Loading containers...", justify="center")
            return table
        table.add_column("Name", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Image", justify="center")
        table.add_column("Memory Usage", justify="center")
        table.add_column("CPU Usage", justify="center")
        for container_config in containers:
            container = dock.get_container(container_config.name)
            stats = dock.get_container_stats(container)
            table.add_row(f'{container_config.name}', f'{container.status}', f'{container.image}',
                          f'{stats["mem_usg_mb"]}', f'{stats["cpu_usg_present"]}')
        grid.add_row("Press Ctrl+C to exit")
        return grid

    def __print_container_status(self, disable_refresh: bool, containers: list[ContainerConfig] = None) -> None:
        console = Console()
        if disable_refresh:
            runs = 1
        else:
            runs = 50
        if containers is None:
            console.print(
                "[blue]Application is not deployed on this system, skipping container report.".center(cs.CLI_WIDTH))
            return
        try:
            dock = DockerHandler()
        except DockerInstanceUnavailable:
            console = Console()
            console.print("[red]Error connecting to local docker daemon".center(cs.CLI_WIDTH))
            console.print("[red]Please make sure docker is running on this system".center(cs.CLI_WIDTH))
            return
        try:
            with Live(self.__generate_container_table(containers, dock, True), auto_refresh=False) as live:
                for run in range(runs):
                    live.update(self.__generate_container_table(containers, dock, False), refresh=True)
                    time.sleep(0.5)
            if not disable_refresh: print("Timeout reached, exiting...")
        except KeyboardInterrupt:
            print("Exit Status Dashboard".center(cs.CLI_WIDTH))

