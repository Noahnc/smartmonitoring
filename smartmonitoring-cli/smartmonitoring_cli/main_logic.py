import logging as lg
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from packaging import version
from rich.console import Console
from rich.table import Table

import smartmonitoring_cli.const_settings as cs
import smartmonitoring_cli.helpers.cli_helper as cli
import smartmonitoring_cli.helpers.deployment_helper as deph
import smartmonitoring_cli.helpers.helper_functions as hf
import smartmonitoring_cli.helpers.log_helper as lh
from smartmonitoring_cli.handlers.data_handler import ConfigError, ManifestError, \
    ValueNotFoundInConfig, InstalledStackInvalid
from smartmonitoring_cli.handlers.data_handler import DataHandler
from smartmonitoring_cli.handlers.docker_handler import DockerHandler, ContainerCreateError, \
    ImageDoesNotExist

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
        """
        Setup logging for the Application.
        :param debug: When True, debug messages are logged
        :param silent: When True, all logs are saved to a file
        :param only_critical: Only critical logs are printed to the console
        """
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
            lg.critical(f'Error loading Config to update file-logger: {e}')
            lh.update_file_logger(level="DEBUG")
            return
        if config.debug_logging:
            lh.update_file_logger(level="DEBUG", size=config.log_file_size_mb, count=config.log_file_count)
        else:
            lh.update_file_logger(size=config.log_file_size_mb, count=config.log_file_count)

    def check_configurations(self, debug: bool) -> None:
        """
        Validate the local config file and the manifest for errors.
        :param debug: Reraise exceptions if True, to print stack trace
        """
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
        """
        Validate the local config file and apply it if changes are present.
        :param silent: Apply changes without asking for confirmation
        """
        if not self.__check_preconditions("applying new configuration skipped"):
            return
        current_config, manifest = self.cfh.get_installed_stack()
        try:
            lg.info("Validating new local configuration...")
            new_config = self.cfh.get_local_config()
            self.cfh.validate_config_against_manifest(new_config, manifest)
        except (ConfigError, ValueNotFoundInConfig) as e:
            lg.error(f'{e}')
            lg.info("You can validate the config file by running 'smartmonitoring validate-config'")
            return
        lg.info("Config file is valid")
        identical, changes = self.cfh.compare_local_config(current_config, new_config)
        if identical:
            lg.warning("No changes found in local config, nothing to apply...")
            return
        if not silent and not cli.print_and_confirm_changes(changes):
            lg.info("Applying new configuration skipped")
            return
        lg.info("Applying new local configuration")
        deph.replace_deployment(current_config, new_config, manifest, manifest, self.cfh, DockerHandler())

    def print_status(self, disable_refresh: bool, banner_version: bool) -> None:
        """
        Prints different information as status-dashboard.
        :param disable_refresh: Print status only once
        :param banner_version: Prints a reduced version of the status dashboard for login banners
        """
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
        """Restarts all containers of the current deployment."""
        if not self.__check_preconditions("restart skipped"):
            return

        lg.info("Restarting smartmonitoring deployment")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        dock.restart_containers(manifest.containers)
        lg.info("All containers restarted successfully")

    def deploy_application(self) -> None:
        """Creates the initial Deployment."""
        if self.__check_if_deployed():
            lg.warning("SmartMonitoring is already deployed, deployment skipped")
            return
        if not hf.check_internet_connection():
            lg.error("No internet connection, deployment skipped")
            return
        lg.info("Performing SmartMonitoring deployment to local docker host")
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
            lg.info("SmartMonitoring application successfully deployed")
        except (ContainerCreateError, ImageDoesNotExist, ValueNotFoundInConfig) as e:
            self.cfh.save_status(status="DeploymentError", error_msg=str(e))
            raise e

    def remove_application(self) -> None:
        """Removes the current Deployment."""
        if not self.__check_preconditions("removal skipped"):
            return
        lg.info("Removing SmartMonitoring deployment from local docker host")
        config, manifest = self.cfh.get_installed_stack()
        dock = DockerHandler()
        deph.uninstall_application(manifest, dock)
        dock.remove_inter_network()
        dock.perform_cleanup()
        self.cfh.remove_var_data_files()
        lg.info("SmartMonitoring application successfully removed")

    def update_application(self, force: bool) -> None:
        """
        Updates the current Deployment if a new version is available in the manifest.
        :param force: Applies the manifest version even if the version is not newer than the current version
        """
        if not self.__check_preconditions("update skipped"):
            return
        if not hf.check_internet_connection():
            lg.error("No internet connection, update skipped")
            return

        lg.info("Retrieving local configuration and update manifest...")
        config, current_manifest = self.cfh.get_installed_stack()
        new_manifest = self.cfh.get_update_manifest(config)

        if not force and not self.__check_version_is_newer(current_manifest.package_version,
                                                           new_manifest.package_version):
            lg.warning("No newer SmartMonitoring Deployment is available, update skipped")
            return
        if force or self.__check_version_is_newer(current_manifest.package_version, new_manifest.package_version):
            lg.info(
                f"Update SmartMonitoring Deployment from {current_manifest.package_version} to {new_manifest.package_version}")
            if deph.replace_deployment(config, config, current_manifest, new_manifest, self.cfh, DockerHandler()):
                lg.info(f"SmartMonitoring Deployment successfully updated to version {new_manifest.package_version}")

    def __check_version_is_newer(self, current_version: str, new_version: str) -> bool:
        """
        Checks if the new version is newer than the current version.
        :param current_version: String of current version
        :param new_version: String of new version
        :return: True if the new version is newer, False otherwise
        """
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
        """
        Checks if the application is already deployed.
        :return: True if the application is deployed, False otherwise
        """
        lg.debug("Checking if SmartMonitoring deployment can be found on local docker host...")
        if self.stack_file.exists():
            lg.debug("SmartMonitoring deployment found on local docker host")
            return True
        else:
            lg.debug("SmartMonitoring deployment not found on local docker host")
            return False

    def __check_if_deployment_in_progress(self) -> bool:
        """
        Checks if the application is currently being deployed.
        If the status is "Deploying" for more than the specified time, the deployment is considered to
        be stuck and False is returned.
        :return: True if the application is currently being deployed, False otherwise
        """
        lg.debug("Checking if SmartMonitoring deployment is currently in progress...")
        if not self.status_file.exists():
            lg.debug("No deployment in progress")
            return False

        data = self.cfh.get_status()
        if data["status"] != "Deploying":
            lg.debug("No deployment in progress...")
            return False

        if data["status"] == "Deploying":
            error_time = datetime.strptime(data["deployment_start"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=cs.DEPLOYMENT_REPAIR_TIMEOUT_MINUTES)
            if error_time < datetime.now():
                lg.debug(f"Last deployment started over {cs.DEPLOYMENT_REPAIR_TIMEOUT_MINUTES} Minutes ago, therefore "
                         f"it is considered to be stuck and no longer in progress")
                return False
        lg.debug(f'Deployment currently in progress, started at: {data["deployment_start"]}')
        return True

    def __check_preconditions(self, message: str) -> bool:
        """
        Checks if the preconditions for the deployment are met.
        :param message: Action that is skipped if the preconditions are not met
        :return: True if the preconditions are met, False otherwise
        """
        if not self.__check_if_deployed():
            lg.warning(f'SmartMonitoring is not deployed, {message}')
            return False
        if self.__check_if_deployment_in_progress():
            lg.warning("A Deployment is already in progress. Please try again later.")
            return False
        return True
