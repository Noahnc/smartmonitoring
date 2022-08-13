import os
from pathlib import Path

from smartmonitoring import const_settings as cs
from smartmonitoring.handlers.data_handler import DataHandler
from smartmonitoring.handlers.docker_handler import DockerHandler
from smartmonitoring.main_logic import MainLogic

PARENT_FOLDER = os.path.dirname(os.path.dirname(__file__))

smartmonitoring_config_dir = os.path.join(PARENT_FOLDER, "config_files")
smartmonitoring_log_dir = os.path.join(PARENT_FOLDER, "logs")
smartmonitoring_var_dir = os.path.join(PARENT_FOLDER, "temp")

stack_file = Path(os.path.join(smartmonitoring_var_dir, cs.DEPLOYED_STACK_FILE_NAME))
status_file = Path(os.path.join(smartmonitoring_var_dir, cs.STATUS_FILE_NAME))
config_file = Path(os.path.join(smartmonitoring_config_dir, cs.LOCAL_CONF_FILE_NAME))

cfh = DataHandler(config_file, stack_file, status_file)
dock = DockerHandler()
main = MainLogic()

config, manifest = cfh.get_installed_stack()

if __name__ == '__main__':
    test = main.get_container_statistics_parallel(manifest.containers)
    print(test)
