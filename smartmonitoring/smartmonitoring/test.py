import os

import const_settings as cs
from handlers.config_handler import ConfigHandler
from main_logic import MainLogic

debug = False
silent = False

PARENT_FOLDER = os.path.dirname(os.path.dirname(__file__))

smartmonitoring_config_dir = os.path.join(PARENT_FOLDER, "config_files")
smartmonitoring_log_dir = os.path.join(PARENT_FOLDER, "logs")
smartmonitoring_var_dir = os.path.join(PARENT_FOLDER, "temp")

config_file = os.path.join(smartmonitoring_config_dir, cs.LOCAL_CONF_FILE_NAME)
stack_file = os.path.join(smartmonitoring_var_dir, cs.DEPLOYED_STACK_FILE_NAME)

cfh = ConfigHandler(config_file, stack_file)

cfh.get_configs()







main = MainLogic()












