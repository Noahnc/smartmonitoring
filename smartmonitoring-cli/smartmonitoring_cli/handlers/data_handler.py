import tempfile
from datetime import datetime

import smartmonitoring_cli.const_settings as cs
import yaml as yaml
import requests
import os
import json
import secrets
from pathlib import Path
import logging as lg
from cerberus import Validator
from deepdiff import DeepDiff
import smartmonitoring_cli.helpers.helper_functions as hf
from smartmonitoring_cli import __version__
from smartmonitoring_cli.models.local_config import LocalConfig
from smartmonitoring_cli.models.update_manifest import UpdateManifest, ContainerConfig, MappedFile
from requests.exceptions import ConnectionError, Timeout, HTTPError
from smartmonitoring_cli.const_settings import ConfigDefaults as cfd
from smartmonitoring_cli.dict_validation_schemas import ValidationSchemas


class ConfigError(Exception):
    pass


class ManifestError(Exception):
    pass


class ValueNotFoundInConfig(Exception):
    pass


class InstalledStackInvalid(Exception):
    pass


class DataHandler:
    def __init__(self, config_file: Path, stack_file: Path, status_file: Path):
        self.config_file = config_file
        self.stack_file = stack_file
        self.status_file = status_file

    def __load_yaml_from_file(self, file: Path) -> dict:
        lg.debug(f'Loading yaml from file: {file}')
        try:
            with open(file, 'r') as stream:
                return yaml.safe_load(stream)
        except OSError as e:
            lg.error(f'Error loading file: {file}, error message: {e}')
            raise

    def __load_yaml_from_web(self, url: str) -> dict:
        """
        Loads a yaml file from a given url and parses it to a dict
        :param url: URL to load yaml from as string
        :return: Dict of yaml file
        """
        tf, file = tempfile.mkstemp(suffix=".yaml")
        lg.debug(f'Downloading yaml from: {url} to: {file}')
        try:
            r = requests.get(url)
            r.raise_for_status()
            with open(file, 'wb') as f:
                f.write(r.content)
            lg.debug(f'Completed download of yaml from: {url} to: {file}')
            return self.__load_yaml_from_file(Path(file))
        finally:
            os.close(tf)
            hf.delete_file_if_exists(file)

    def get_update_manifest(self, local_config: LocalConfig) -> UpdateManifest:
        """
        Loads the update manifest from the given url in the local config.
        Raises an ManifestError on failure.
        :param local_config: LocalConfig object for which to load the update manifest
        :return: Returns the update manifest as UpdateManifest object
        """
        lg.debug(f'Loading update manifest for channel: {local_config.update_channel}')
        try:
            manifest = self.__load_yaml_from_web(local_config.update_manifest_url)
            stack = manifest["versions"][local_config.update_channel]
        except (ConnectionError, HTTPError, Timeout) as e:
            raise ManifestError(f'Error downloading manifest: {e}') from e
        except yaml.YAMLError as e:
            raise ManifestError(f'Error parsing yaml of manifest: {e}') from e
        except KeyError as e:
            raise ManifestError(f'Update channel: {local_config.update_channel} not found in update manifest') from e
        return self.process_update_manifest(stack)

    def get_local_config(self) -> LocalConfig:
        """
        Loads the local config from the local file system.
        Raises a ConfigError on failure.
        :return: LocalConfig object
        """
        lg.debug(f'Loading local config from: {self.config_file}')
        try:
            config = self.__load_yaml_from_file(self.config_file)
            smartmonitoring_config = config["SmartMonitoring_Proxy"]
        except OSError as e:
            raise ConfigError(f'Error loading local config file, message: {e}') from e
        except KeyError as e:
            raise ConfigError(f'No Key "SmartMonitoring_Proxy" found in local config file: {self.config_file}') from e
        except yaml.YAMLError as e:
            raise ConfigError(f'Error parsing yaml of local config: {e}') from e
        self.__set_default_values_in_local_config(smartmonitoring_config)
        return self.process_local_config(smartmonitoring_config)

    def process_update_manifest(self, update_manifest: dict) -> UpdateManifest:
        """
        Validates the manifest and converts it to an UpdateManifest object.
        Raises a ManifestError on failure.
        :param update_manifest: Dict of the update manifest
        :return: UpdateManifest object
        """
        lg.debug('Processing update manifest from dict to object')
        valid, message = self.validate_update_manifest(update_manifest)
        if not valid:
            raise ManifestError(f'Update manifest not valid: {message}')
        try:
            manifest = UpdateManifest.from_dict(update_manifest)
        except Exception as e:
            lg.error(f'Error phrasing update manifest from dict to object: {e}')
            raise ManifestError(f'Error phrasing update manifest from dict to object: {e}') from e
        lg.debug('Update manifest dict successfully processed to object')
        return manifest

    def validate_config_against_manifest(self, config: LocalConfig, manifest: UpdateManifest,
                                         check_files: bool = True) -> None:
        """
        Validates the local config against the manifest by composing all environment variables and mapped files for
        each container.
        If validation fails, an Exception is raised.
        :param manifest: UpdateManifest object
        :param check_files: If files should also be checked
        :param config: LocalConfig object
        """
        lg.debug("Validating local config against update manifest")
        env_secrets = self.generate_dynamic_secrets(manifest.dynamic_secrets)
        for container in manifest.containers:
            self.compose_env_variables(config, container, env_secrets)
            if container.files is not None and check_files:
                self.compose_mapped_files(container, config)

    def process_local_config(self, local_config: dict) -> LocalConfig:
        """
        Validates the local config and converts it to a LocalConfig object.
        :param local_config: Local config as dict
        :return: LocalConfig object
        """
        lg.debug("Processing local config from dict to object")
        valid, message = self.validate_local_config(local_config)
        if not valid:
            raise ConfigError(f'Local config not valid: {message}')
        try:
            config = LocalConfig.from_dict(local_config)
        except Exception as e:
            raise ConfigError(f'Error converting local config to object. Error message: {e})') from e
        lg.debug("Local config dict successfully processed to object")
        return config

    def compose_env_variables(self, local_config: LocalConfig, container: ContainerConfig,
                              cont_secrets: dict) -> dict:
        """
        Composes all environment variables for a given container.
        :param local_config: Local config object
        :param container: ContainerConfig object for which to compose the environment variables
        :param cont_secrets: Dict of generated secrets
        :return: Dict of environment variables for the given container
        """
        env_variables = container.config.static.copy()
        container_local_config = {}
        try:
            container_local_config = self.__get_container_settings_from_local_config(local_config, container)
        except ValueNotFoundInConfig:
            if container.config.dynamic is not None:
                lg.error(
                    f'Container has dynamic Config specified, but no configuration has been found in the local config '
                    f'for container: {container.name}')
                raise ValueNotFoundInConfig(f'Missing config for container: {container.name}')

        # Combine settings of local config and manifest, settings of local config take precedence
        if "local_settings" in container_local_config:
            if container_local_config["local_settings"] is not None:
                env_variables = env_variables | container_local_config["local_settings"]

        if container.config.secrets is not None:
            env_variables = env_variables | self.__compose_env_variables_secrets(container, cont_secrets)

        if container.config.dynamic is not None:
            env_variables = env_variables | self.__compose_env_variables_dynamic(container_local_config, container)

        return env_variables

    def __compose_env_variables_dynamic(self, container_local_config: dict, container: ContainerConfig) -> dict:
        """
        Composes the dynamic config for a given container to env. variables.
        For each dynamic config entry, the corresponding value is looked up in the local config and added to the env.
        variables dict.
        :param container_local_config: The local config dict for the given container
        :param container: ContainerConfig object for which to compose the dynamic environment variables
        :return: Dict of all dynamic env. variables for the given container
        """
        env_variables = {}
        # Pull value for each dynamic setting of the container from the local config
        if container.config.dynamic is None:
            return env_variables
        for key, value in container.config.dynamic.items():
            if value not in container_local_config:
                raise ValueNotFoundInConfig(
                    f'Dynamic setting {value} not found in local config for container: {container.name}')
            if key in env_variables:
                raise ManifestError(f'Dynamic setting {key} already exists in  settings of container: {container.name}')
            val = container_local_config[value]
            env_variables[key] = val
        return env_variables

    def __compose_env_variables_secrets(self, container: ContainerConfig, cont_secrets: dict) -> dict:
        """
        Composes the secrets for a given container to env. variables.
        For each secret of the container, the corresponding value is looked up in the generated secrets dict and added
        to the env. variables dict.
        :param container: ContainerConfig object for which to compose the secrets
        :param cont_secrets: Dict of all global deployment secrets
        :return: Dict of all secrets as env. variables for the given container
        """
        env_variables = {}
        # Pull secret value for each secret of the container from the global dynamic secrets dict
        for key, value in container.config.secrets.items():
            lg.debug(f'Composing the following secrets for container: {container.name}:')
            lg.debug(container.config.secrets)
            if value not in cont_secrets:
                lg.error(f'Secret {value} not found in global dynamic secrets')
                raise ManifestError(f'Secret {value} of container {container.name} not found in secrets list')
            if value in env_variables:
                lg.error(f'Value {value} defined multiple times for container {container.name}')
                raise ManifestError(
                    f'Variable {value} of container {container.name} already defined in env variables')
            env_variables[key] = cont_secrets[value]
        return env_variables

    def __set_default_values_in_local_config(self, config: dict) -> None:
        """
        Sets default values in the local config if they are not set.
        :param config: Dict of local config
        """
        self.__set_default_value_for_key(config, "update_channel", cfd.UPDATE_CHANNEL)
        self.__set_default_value_for_key(config, "debug_logging", cfd.ENABLE_DEBUG_LOGGING)
        self.__set_default_value_for_key(config, "log_file_size_mb", cfd.LOG_FILE_SIZE_LIMIT_MB)
        self.__set_default_value_for_key(config, "log_file_count", cfd.LOG_FILE_COUNT_LIMIT)

    def __set_default_value_for_key(self, dictionary: dict, key: str, value: str) -> None:
        """
        Sets the default value for a given key in a dict if the key is not set.
        :param dictionary: dictionary in which to set the default value
        :param key: Key for which to set the default value
        :param value: Value to set if current value is None
        """
        if key not in dictionary:
            lg.debug(f'Setting default value for key: {key} to: {value}')
            dictionary[key] = value

    def __get_container_settings_from_local_config(self, config: LocalConfig, container: ContainerConfig) -> dict:
        """
        Returns the settings for a given container from the local config.
        :param config: LocalConfig object to get the settings from
        :param container: Container for which to get the settings
        :return: Dict of settings for the given container
        """
        lg.debug(f'Getting config of container: {container.name}')
        try:
            container_local_config = getattr(config, container.name)
            lg.debug(f'Config of container: {container.name} successfully retrieved')
            return container_local_config.to_dict()
        except AttributeError as e:
            lg.debug(f'No config for container: {container.name} in local config found')
            raise ValueNotFoundInConfig(f'Config for container {container.name} missing') from e

    def __get_local_setting_of_container(self, local_config: LocalConfig, container: ContainerConfig, key: str):
        """
        Get specific local_setting of a given container from the local config file.
        :param local_config: LocalConfig object to get the settings from
        :param container: Container for which to get the settings
        :param key: Value of this key is returned
        :return: Returns the value of the given key
        """
        try:
            container_local_config = self.__get_container_settings_from_local_config(local_config, container)
            lg.debug(f'Reading Key: {key} from local config of container: {container.name}')
            value = container_local_config[key]
            lg.debug(f'Value for key: {key} is: {value}')
            if value is None:
                raise ValueNotFoundInConfig(
                    f'Value for key: {key} is not found in local config of container: {container.name}')
            return value
        except KeyError as e:
            lg.error(f'No key: {key} in local config of Container {container} found')
            raise ValueNotFoundInConfig(f'No key: {key} in local config of Container {container} found') from e

    def __validate_dict(self, data: dict, schema: dict) -> tuple[bool, str]:
        """
        Validates a given dict against a given schema.
        :param data: Dict of data to validate
        :param schema: schema as dict to validate against
        :return: Tuple of bool and str. Bool indicates if the validation was successful, str contains the error message
        """
        v = Validator(schema)
        if v.validate(data):
            lg.debug("Dict successfully validated with schema: " + str(schema))
            return True, "Config is Valid"
        else:
            lg.warning("Dict validation error: " + str(v.errors))
            return False, "Error found in Configuration: " + str(v.errors)

    def validate_update_manifest(self, manifest: dict) -> tuple[bool, str]:
        """
        Validates the update manifest against the schema.
        :param manifest: manifest as dict
        :return: Tuple of bool and str. Bool indicates if the validation was successful, str contains the error message
        """
        assert isinstance(manifest, dict)
        return self.__validate_dict(manifest, ValidationSchemas.MANIFEST)

    def validate_local_config(self, config: dict) -> tuple[bool, str]:
        """
        Validates the local config against the schema.
        :param config: Local config as dict
        :return: Tuple of bool and str. Bool indicates if the validation was successful, str contains the error message
        """
        assert isinstance(config, dict)
        return self.__validate_dict(config, ValidationSchemas.LOCAL_CONFIG)

    def get_config_and_manifest(self) -> tuple[LocalConfig, UpdateManifest]:
        """
        Returns both the local config and the corresponding update manifest downloaded from the url specified in the
        local config file.
        :return: Tuple of LocalConfig and UpdateManifest objects
        """
        config = self.get_local_config()
        manifest = self.get_update_manifest(config)
        return config, manifest

    def save_installed_stack(self, config: LocalConfig, manifest: UpdateManifest) -> None:
        """
        Saves both, the local config and the manifest combined in a file serialized as json.
        :param config: LocalConfig object to save
        :param manifest: UpdateManifest object to save
        """
        lg.debug(f'Saving  stack to file: {self.stack_file}')
        try:
            stack = {
                "manifest": manifest.to_dict(),
                "config": config.to_dict()
            }
        except Exception as e:
            lg.error(f'Error composing dict to save to stack file: {self.stack_file}')
            raise InstalledStackInvalid(f'Error composing stack to dict {e}')
        self.__save_json_file(self.stack_file, stack)

    def compose_mapped_files(self, container: ContainerConfig, config: LocalConfig) -> list[MappedFile]:
        """
        Composes a list of MappedFile objects for the given container.
        If a MappedFile object users a dynamic path, the path looked up in the local config and used as the new path.
        If one of the files does not exist in the local filesystem, an exception is raised.
        :param container: ContainerConfig object for which to compose the MappedFile objects
        :param config: LocalConfig object to look up the dynamic paths
        :return: A list of MappedFile objects
        """
        container_files = []
        for file in container.files:
            if not file.host_path_dynamic:
                if not os.path.exists(file.host_path):
                    raise ManifestError(f'Host path {file.host_path} does not exist on this system')
                container_files.append(file)
            else:
                host_path = self.__get_local_setting_of_container(config, container, file.host_path)
                if not os.path.exists(host_path):
                    raise ConfigError(f'File {file.name} does not exist on this system')
                container_files.append(MappedFile(file.name, host_path, file.host_path_dynamic, file.container_path))

        return container_files

    def get_installed_stack(self) -> tuple[LocalConfig, UpdateManifest]:
        """
        Loads the installed stack from the stack file and processes the local config and manifest from it back to
        objects.
        :return: Tuple of LocalConfig and UpdateManifest objects
        """
        try:
            stack = self.__load_json_file(self.stack_file)
            config = self.process_local_config(stack["config"])
            manifest = self.process_update_manifest(stack["manifest"])
            return config, manifest
        except Exception as e:
            raise InstalledStackInvalid(f'Error getting installed stack from file: {self.stack_file}, message: {e}')

    def save_status(self, status: str, upd_channel: str = None, pkg_version: str = None, error_msg: str = "-") -> None:
        """
        Saves the status file with the given status, update channel, package version and error message.
        :param status: Status of the current deployment process
        :param upd_channel: Channel of the current deployment
        :param pkg_version: Version of the current deployment
        :param error_msg: Error message that occurred during the deployment process
        """
        deployment_start = None

        # Check if a not allowed status is given
        allowed_statuses = ["Deployed", "Deploying", "DeploymentError"]
        if status not in allowed_statuses:
            raise ValueError(f'Invalid status: {status}, allowed statuses: {allowed_statuses}')

        if not self.status_file.exists():
            if pkg_version is None: pkg_version = "-"
            if upd_channel is None: upd_channel = "-"
            if status == "Deployed":
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif status == "Deploying":
                last_update = "-"
                deployment_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_update = "-"
            data = {
                "status": status,
                "error_msg": error_msg,
                "smartmonitoring_version": __version__,
                "update_channel": upd_channel,
                "package_version": pkg_version,
                "last_update": last_update,
                "deployment_start": deployment_start
            }
        else:
            data = self.get_status()
            if pkg_version is None: pkg_version = data["package_version"]
            if upd_channel is None: upd_channel = data["update_channel"]
            if status == "Deployed":
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif status == "Deploying":
                last_update = data["last_update"]
                deployment_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_update = data["last_update"]
            data["status"] = status
            data["error_msg"] = error_msg
            data["smartmonitoring_version"] = __version__
            data["update_channel"] = upd_channel
            data["package_version"] = pkg_version
            data["last_update"] = last_update
            data["deployment_start"] = deployment_start

        lg.debug(f'Saving status: {status}')
        self.__save_json_file(self.status_file, data)

    def get_status(self) -> dict:
        """
        Loads the status file and returns it as dict.
        :return: Content of the status file as dict
        """
        lg.debug(f'Getting status from file: {self.status_file}')
        try:
            status = self.__load_json_file(self.status_file)
            return status
        except Exception:
            lg.error(f'Error getting status from file: {self.status_file}')
            raise

    def __save_json_file(self, file: os.path, data: dict) -> None:
        """
        Saves the given data as json to the given file.
        :param file: File to save the data to
        :param data: Data as dict to save as json
        """
        lg.debug(f'Saving data to json file: {file}')
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)

    def __load_json_file(self, file: os.path) -> dict:
        """
        Loads the given json file and returns it as dict.
        :param file: File to load json from
        :return: Dict of processed json file content
        """
        lg.debug(f'Loading data from json file: {file}')
        try:
            with open(file) as f:
                data = json.load(f)
        except Exception:
            lg.error(f'Could not load json from file: {file}')
            raise
        return data

    def remove_var_data_files(self) -> None:
        """
        Remove all variable files created by this application.
        """
        if os.path.exists(self.stack_file):
            lg.debug(f'Removing stack file: {self.stack_file}')
            os.remove(self.stack_file)
        if os.path.exists(self.status_file):
            lg.debug(f'Removing status file: {self.status_file}')
            os.remove(self.status_file)

    def generate_dynamic_secrets(self, secret_names: list[str]) -> dict:
        """
        Generates a dynamic password for each secret name in the given list.
        :param secret_names: List of secret names to generate a password for
        :return: Dict of all secrets with key as name and value as password
        """
        dock_secrets = {}
        for secret in secret_names:
            if secret in dock_secrets:
                raise ManifestError(f'Secret {secret} is defined multiple times in manifest')
            sec_string = secrets.token_urlsafe(cs.DYNAMIC_SECRET_KEY_LENGTH)
            dock_secrets[secret] = sec_string
        return dock_secrets

    def compare_local_config(self, old_config: LocalConfig, new_config: LocalConfig) -> tuple[bool, str]:
        """
        Compares the given local configs and returns if they are equal and a message with changes that have been
        found. :param old_config: Old Config as LocalConfig object :param new_config: New Config as LocalConfig
        object :return: Tuple of bool and string. Bool is True if configs are equal, False if not. String is a
        message with all changes that have been found.
        """
        lg.debug(f'Comparing current config with new config')
        return self.__compare_dicts(old_config.to_dict(), new_config.to_dict())

    def __compare_dicts(self, old_dict: dict, new_dict: dict) -> tuple[bool, str]:
        """
        Compares the given dicts and returns if they are equal and a message with changes that have been found.
        :param old_dict: Old dict to compare
        :param new_dict: New dict to compare
        :return: Tuple of bool and string. Bool is True if dicts are equal, False if not. String is a message containing
        all found changes.
        """
        difference = DeepDiff(old_dict, new_dict)
        difference.items()
        if not difference:
            lg.debug("The two dicts are the same")
            return True, "-"
        stats = difference.get_stats()
        lg.debug(f'{stats["DIFF COUNT"]} changes found')
        return False, difference.pretty()
