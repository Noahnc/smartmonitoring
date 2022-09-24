import logging as lg
import os
import platform
import socket
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import psutil
from packaging import version
from rich.console import Console
from rich.live import Live
from rich.table import Table

import smartmonitoring_cli.const_settings as cs
import smartmonitoring_cli.helpers.cli_helper as cli
import smartmonitoring_cli.helpers.deployment_helper as deph
import smartmonitoring_cli.helpers.helper_functions as hf
import smartmonitoring_cli.helpers.log_helper as lh
from smartmonitoring_cli import __version__
from smartmonitoring_cli.handlers.data_handler import ConfigError, ManifestError, \
    ValueNotFoundInConfig, InstalledStackInvalid
from smartmonitoring_cli.handlers.data_handler import DataHandler
from smartmonitoring_cli.handlers.docker_handler import DockerHandler, ContainerCreateError, \
    ImageDoesNotExist
from smartmonitoring_cli.models.local_config import LocalConfig
from smartmonitoring_cli.models.update_manifest import UpdateManifest, ContainerConfig

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

    def setup_logging(self, debug: bool, silent: bool, only_critical: bool = False) -> None:
        log_file_path = os.path.join(self.smartmonitoring_log_dir, cs.LOG_FILE_NAME)
        if not silent and not only_critical:
            lh.add_console_logger(debug)
            return
        if not silent and only_critical:
            lh.add_console_logger(debug, level="CRITICAL")
            return
        if debug:
            lh.setup_file_logger(file=log_file_path)
            return

        lh.setup_file_logger(file=log_file_path, level="INFO")
        if not self.__check_if_deployed():
            lh.update_file_logger(level="DEBUG")
            return
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

    def check_configurations(self, debug: bool) -> None:
        config_valid = True
        config_message = "Local Config is valid"
        manifest_valid = True
        manifest_message = "Manifest is valid"

        try:
            config, manifest = self.cfh.get_config_and_manifest()
            self.cfh.validate_config_against_manifest(config, manifest, check_files=False)
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
        table.add_row("[bright_cyan]Valid", "[bright_cyan]Valid")
        table.add_row(f'[green]{config_valid}' if config_valid else f'[red]{config_valid}',
                      f'[green]{manifest_valid}' if manifest_valid else f'[red]{manifest_valid}')
        table.add_row()
        table.add_row("[bright_cyan]Message", "[bright_cyan]Message")
        table.add_row(f'[green]{config_message}' if config_valid else f'[red]{config_message}',
                      f'[green]{manifest_message}' if manifest_valid else f'[red]{manifest_message}')
        table.add_row()

        Console().print(table)

    def validate_and_apply_config(self, silent: bool) -> None:
        if not self.__check_preconditions("skip applying new configuration..."):
            return
        current_config, manifest = self.cfh.get_installed_stack()
        try:
            lg.info("Validating new local configuration...")
            new_config = self.cfh.get_local_config()
            self.cfh.validate_config_against_manifest(new_config, manifest)
        except (ConfigError, ValueNotFoundInConfig) as e:
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
        deph.replace_deployment(current_config, new_config, manifest, manifest)

    def print_status(self, disable_refresh: bool, banner_version: bool) -> None:
        cli.print_logo()
        if self.__check_if_deployed():
            config, manifest = self.cfh.get_installed_stack()
            if not banner_version:
                cli.print_system_status(self.cfh, config, manifest)
                cli.print_live_updating_tables(disable_refresh, manifest.containers)
            else:
                cli.print_logon_banner(config, manifest)
        else:
            if not banner_version:
                cli.print_system_status(self.cfh)
                cli.print_live_updating_tables(disable_refresh)
            else:
                cli.print_logon_banner()

    def restart_application(self) -> None:
        if not self.__check_preconditions("skipping restart..."):
            return

        lg.info("Restarting smartmonitoring deployment...")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        dock.restart_containers(manifest.containers)
        lg.info("All containers restarted successfully...")

    def deploy_application(self) -> None:
        if self.__check_if_deployed():
            lg.warning("SmartMonitoring is already deployed, skipping deployment...")
            return
        if not hf.check_internet_connection():
            lg.error("No internet connection, skipping deployment...")
            return
        lg.info("Deploying smartmonitoring application to this system...")
        lg.info("Retrieving local configuration and update manifest...")
        config, manifest = self.cfh.get_config_and_manifest()
        dock = DockerHandler()
        self.cfh.save_status("Deploying")
        try:
            self.cfh.validate_config_against_manifest(config, manifest)
            dock.pull_images(manifest.containers)
            dock.create_inter_network()
            deph.install_deployment(config, manifest, dock, self.cfh)
            self.cfh.save_installed_stack(config, manifest)
            self.cfh.save_status("Deployed", upd_channel=config.update_channel, pkg_version=manifest.package_version)
            lg.info("SmartMonitoring application successfully deployed...")
        except (ContainerCreateError, ImageDoesNotExist, ValueNotFoundInConfig) as e:
            self.cfh.save_status(status="DeploymentError", error_msg=str(e))
            raise e

    def remove_application(self) -> None:
        if not self.__check_preconditions("skipping removal..."):
            return
        lg.info("Removing smartmonitoring deployment from this system...")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        deph.uninstall_application(manifest, dock)
        dock.remove_inter_network()
        dock.perform_cleanup()
        self.cfh.remove_var_data_files()
        lg.info("SmartMonitoring application successfully removed")

    def update_application(self, force: bool) -> None:
        if not self.__check_preconditions("skipping update..."):
            return
        if not hf.check_internet_connection():
            lg.error("No internet connection, skipping update...")
            return

        lg.info("Retrieving local configuration and update manifest...")
        config, current_manifest = self.cfh.get_installed_stack()
        new_manifest = self.cfh.get_update_manifest(config)

        if not force and not self.__check_version_is_newer(current_manifest.package_version,
                                                           new_manifest.package_version):
            lg.warning("No newer SmartMonitoring Deployment is available, skipping update...")
            return
        if force or self.__check_version_is_newer(current_manifest.package_version, new_manifest.package_version):
            lg.info(
                f"Update SmartMonitoring from {current_manifest.package_version} to {new_manifest.package_version}...")
            if deph.replace_deployment(config, config, current_manifest, new_manifest, self.cfh, DockerHandler()):
                lg.info(f"SmartMonitoring successfully updated to version {new_manifest.package_version}")

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

    def __check_if_deployment_in_progress(self) -> bool:
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

    def __check_preconditions(self, Message: str) -> bool:
        if not self.__check_if_deployed():
            lg.warning(f'SmartMonitoring is not deployed, {Message}')
            return False
        if self.__check_if_deployment_in_progress():
            lg.warning("A Deployment is already in progress. Please try again later.")
            return False
        return True
