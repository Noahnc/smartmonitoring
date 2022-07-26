from itertools import count
import tempfile
import yaml as yaml
import requests
import os
import json
import secrets
import logging as lg
from cerberus import Validator
from deepdiff import DeepDiff
import helpers.helper_functions as hf
from models.local_config import LocalConfig
from models.update_manifest import UpdateManifest, ContainerConfig
from requests.exceptions import ConnectionError, Timeout, HTTPError
from const_settings import ConfigDefaults as cfd
from dict_validation_schemas import ValidationSchemas

class ConfigValidationError(Exception):
    pass

class ManifestValidationError(Exception):
    pass

class FileDownloadError(Exception):
    pass

class FileError(Exception):
    pass

class ValueNotFoundInConfig(Exception):
    pass

class InstalledStackInvalid(Exception):
    pass


class ConfigHandler:
    def __init__(self, config_file: os.path, deployed_stack_file: os.path):
        self.config_file = config_file
        self.stack_file = deployed_stack_file

    def load_yaml_from_file(self, file: str) -> dict:
        lg.debug("Loading yaml from file: " + str(file))
        try:
            with open(file, 'r') as stream:
                return yaml.safe_load(stream)
        except OSError as e:
            lg.error(f'Error loading file: {file}, error message: {e}')
            raise FileError(f'Error loading file: {file}, error message: {e}') from e
        except yaml.YAMLError as e:
                lg.error(f'Yaml in file {file} is invalid, error message: {e}')
                raise FileError(f'Yaml in file {file} is invalid, error message: {e}') from e

    def load_yaml_from_web(self, url: os.path) -> dict:
        tf, file = tempfile.mkstemp(suffix=".yaml")
        lg.debug(f'Downloading yaml from: {url} to: {file}')
        try:
            r = requests.get(url)  
            with open(file, 'wb') as f:
                f.write(r.content)
            lg.debug(f'Completed download of yaml from: {url} to: {file}')
            return self.load_yaml_from_file(file)
        except ConnectionError or HTTPError or Timeout as e:
            lg.error(f'Error downloading yaml from: {url} to: {file}, error message: {e}')
            raise FileDownloadError(f'Could not connect to url {url}, error message: {e}') from e
        finally:
            os.close(tf)
            hf.delete_file_if_exists(file)

    def get_update_manifest(self, local_config: LocalConfig) -> UpdateManifest:
        lg.debug(f'Loading update manifest for channel: {local_config.update_channel}')
        manifest = self.load_yaml_from_web(local_config.update_manifest_url)
        try:
            stack = manifest["versions"][local_config.update_channel]
        except KeyError as e:
                lg.error(f'Update channel: {local_config.update_channel} not found in update manifest')
                raise ManifestValidationError(f'Update channel: {local_config.update_channel} not found in update manifest') from e
        return self.process_update_manifest(stack)
        
    def get_local_config(self) -> LocalConfig:
        lg.debug(f'Loading local config from: {self.config_file}')
        config = self.load_yaml_from_file(self.config_file)
        try:
            smartmonitoring_config = config["SmartMonitoring_Proxy"]
        except KeyError as e:
                lg.error(f'No Key "SmartMonitoring_Proxy" found in local config file: {self.config_file}')
                raise ConfigValidationError(f'No Key "SmartMonitoring_Proxy" found in local config file: {self.config_file}') from e
        self.__set_default_values_in_local_config(smartmonitoring_config)
        return self.process_local_config(smartmonitoring_config)

    def process_update_manifest(self, update_manifest: dict) -> UpdateManifest:
        lg.debug('Processing update manifest from dict to object')
        valid, message = self.validate_update_manifest(update_manifest)
        if not valid:
            lg.error(f'Update manifest not valid: {message}')
            raise ManifestValidationError(f'Update manifest not valid: {message}')
        try:
            manifest = UpdateManifest.from_dict(update_manifest)
        except Exception as e:
            lg.error(f'Error phrasing update manifest from dict to object: {e}')
            raise ManifestValidationError(f'Error phrasing update manifest from dict to object: {e}') from e
        else:
            lg.debug('Update manifest dict successfully processed to object')
        return manifest
    
    def validate_container_configs(self, config: LocalConfig, manifest: UpdateManifest) -> None:
        lg.debug("Validating container configs in local config and update manifest")
        env_secrets = self.generate_dynamic_secrets(manifest.dynamic_secrets)
        for container in manifest.containers:
            self.compose_env_variables(config, container, env_secrets)

    def process_local_config(self, local_config: dict) -> LocalConfig:
        lg.debug("Processing local config from dict to object")
        valid, message = self.validate_local_config(local_config)
        if not valid:
            lg.critical(f'Local config not valid: {message}')
            raise ConfigValidationError(f'Local config not valid: {message}')
        try:
            config = LocalConfig.from_dict(local_config)
        except Exception as e:
            lg.critical("Error converting local config to object.")
            raise ConfigValidationError(f'Error converting local config to object. Error message: {e})') from e
        else:
            lg.debug("Local config dict successfully processed to object")
        return config

    # Generates dict of environment variables for a container
    def compose_env_variables(self, local_config: LocalConfig, container: ContainerConfig, cont_secrets:list[dict]) -> dict:
        env_variables = container.config.static.copy()
        container_local_config = {}
        try:
            container_local_config = self.__get_container_settings_from_local_config(local_config, container)
        except ValueNotFoundInConfig as e:
            if container.config.dynamic is not None:
                lg.error(f'Container has dynamic Config specified, but no configuration has been found in the local config for container: {container.name}')
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
        env_variables = {}
        # Pull value for each dynamic setting of the container from the local config
        if container.config.dynamic is not None:
            for key, value in container.config.dynamic.items():
                if value not in container_local_config:
                    raise ValueNotFoundInConfig(f'Dynamic setting {value} not found in local config for container: {container.name}')
                val = container_local_config[value]
                env_variables[key] = val
        return env_variables
    
    def __compose_env_variables_secrets(self, container: ContainerConfig, cont_secrets:list[dict]) -> dict:
        env_variables = {}
        # Pull secret value for each secret of the container from the global dynamic secrets dict
        for key, value in container.config.secrets.items():
            lg.debug(f'Composing the follwing secrets for container: {container.name}:')
            lg.debug(container.config.secrets)
            if value not in cont_secrets:
                lg.error(f'Secret {value} not found in global dynamic secrets')
                raise ManifestValidationError(f'Secret {value} of container {container.name} not found in secrets list')
            if value in env_variables:
                lg.error(f'Value {value} defined multiple times for container {container.name}')
                raise ManifestValidationError(f'Variable {value} of container {container.name} already defined in env variables')
            env_variables[key] = cont_secrets[value]
        return env_variables
    
    def __set_default_values_in_local_config(self, config: dict) -> dict:
        self.__set_default_value_for_key(config, "update_channel", cfd.UPDATE_CHANNEL)
        self.__set_default_value_for_key(config, "debug_logging", cfd.ENABLE_DEBUG_LOGGING)
        self.__set_default_value_for_key(config, "log_file_size_mb", cfd.LOG_FILE_SIZE_LIMIT_MB)
        self.__set_default_value_for_key(config, "log_file_count", cfd.LOG_FILE_COUNT_LIMIT)
            
            
    def __set_default_value_for_key(self, dictionary: dict, key: str, value: str) -> None:
        if key not in dictionary:
            lg.debug(f'Setting default value for key: {key} to: {value}')
            dictionary[key] = value
    
    def __get_container_settings_from_local_config(self, config: LocalConfig, container: ContainerConfig) -> dict:
        lg.debug(f'Getting config of container: {container.name}')
        try:
            container_local_config = getattr(config, container.name)
            lg.debug(f'Config of container: {container.name} successfully retrieved')
            return container_local_config.to_dict()
        except AttributeError as e:
            lg.info(f'No config for container: {container.name} in local config found')
            raise ValueNotFoundInConfig(f'Config for container {container.name} missing') from e
        
    def get_value_from_local_config(self, local_config: LocalConfig, container: ContainerConfig, key: str) -> str:
        try:
            lg.debug(f'Getting config of container: {container.name}')
            container_local_config = getattr(local_config, container.name).to_dict()
            lg.debug(f'Reading Key: {key} from local config of container: {container.name}')
            value = container_local_config[key]
            lg.debug(f'Value for key: {key} is: {value}')
            if value is None:
                raise ValueNotFoundInConfig(f'Value for key: {key} is not found in local config of container: {container.name}')
            return value
        except AttributeError as e:
            lg.error(f'No config for container: {container.name} in local config found')
            raise ValueNotFoundInConfig(f'No config for container: {container.name} in local config found') from e
        except KeyError as e:
            lg.error(f'No key: {key} in local config of Container {container} found')
            raise ValueNotFoundInConfig(f'No key: {key} in local config of Container {container} found') from e
        

    def __validate_dict(self, config: dict, schema: dict) -> tuple[bool, str]:
        v = Validator(schema)
        if v.validate(config):
            lg.debug("Config successfully validated with schema: " + str(schema))
            return (True, "Config is Valid")
        else:
            lg.warning("Dict validation error: " + str(v.errors))
            return (False, "Error found in Configuration: " + str(v.errors))
        
    def validate_update_manifest(self, config: dict) -> tuple[bool, str]:
        assert isinstance(config, dict)
        return self.__validate_dict(config, ValidationSchemas.MANIFEST)

    def validate_local_config(self, config: dict) -> tuple[bool, str]:
        assert isinstance(config, dict)
        return self.__validate_dict(config, ValidationSchemas.LOCAL_CONFIG)

    def get_configs(self) -> tuple[LocalConfig, UpdateManifest]:
        config = self.get_local_config()
        manifest = self.get_update_manifest(config)
        self.validate_container_configs(config, manifest)
        return config, manifest

    def save_installed_stack(self, local_config: LocalConfig, manifest: UpdateManifest, status: str) -> None:
        lg.debug(f'Saving installed stack from file: {self.stack_file}')
        try:
            dict = {
                "Status": status,
                "manifest": manifest.to_dict(),
                "config": local_config.to_dict()
            }
        except Exception as e:
            lg.error(f'Error composing dict to save to stack file: {self.stack_file}')
            raise InstalledStackInvalid(f'Error composing stack to dict {e}')
        with open(self.stack_file, 'w') as f:
            json.dump(dict, f, indent=4)
            
    def get_installed_stack(self) -> tuple[LocalConfig, UpdateManifest, str]:
        lg.debug(f'Loading installed stack from file: {self.stack_file}')
        try:
            with open(self.stack_file) as f:
                dict = json.load(f)
        except Exception as e:
            lg.critical(f'Could not load installed stack from file: {self.stack_file}')
            raise InstalledStackInvalid(f'Could not load installed stack from file: {self.stack_file}')
        
        try:
            config = self.process_local_config(dict["config"])
            manifest = self.process_update_manifest(dict["manifest"])
            status = dict["Status"]
            return config, manifest, status
        except Exception as e:
            lg.critical(f'Error processing installed stack from file: {self.stack_file}, message: {e}')
            raise InstalledStackInvalid(f'Error processing installed stack from file: {self.stack_file}, message: {e}')
            
    def remove_installed_stack(self) -> None:
        if self.check_if_stack_file_exists:
            os.remove(self.stack_file)
            lg.debug(f'Stack file removed: {self.stack_file}')
        
    def check_if_stack_file_exists(self) -> bool:
        lg.debug(f'Checking if stack is installed from file: {self.stack_file}')
        if os.path.exists(self.stack_file):
            lg.debug(f'Stack is installed: {self.stack_file}')
            return True
        else:
            lg.debug(f'Stack file does not exist: {self.stack_file}')
            return False
    
    def generate_dynamic_secrets(self, secret_names: list[str]) -> dict:
        dock_secrets = {}
        for secret in secret_names:
            if secret in dock_secrets:
                raise ManifestValidationError(f'Secret {secret} is defined multiple times in manifest')
            sec_string = secrets.token_urlsafe(16)
            dock_secrets[secret] = sec_string
        return dock_secrets
        
    def compare_local_config(self, old_config: LocalConfig, new_config: LocalConfig) -> tuple[bool, str]:
        lg.debug(f'Comparing current config with new config')
        return self.__compare_dicts(old_config.to_dict(), new_config.to_dict())
        
    def __compare_dicts(self, old_dict: dict, new_dict: dict) -> tuple[bool, str]:
        difference = DeepDiff(old_dict, new_dict)
        difference.items()
        if not difference:
            lg.debug("The two dicts are the same")
            return True, "-"
        stats = difference.get_stats()
        lg.debug(f'{stats["DIFF COUNT"]} changes found')
        return False, difference.pretty()
        

            
    