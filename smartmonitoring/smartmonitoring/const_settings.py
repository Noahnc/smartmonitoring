# Width of the cli interface
CLI_WIDTH = 110

# Name of different files
LOG_FILE_NAME = 'smartmonitoring-helper.log'
LOCAL_CONF_FILE_NAME = 'smartmonitoring_config.yaml'
DEPLOYED_STACK_FILE_NAME = 'installed_stack.json'

CLI_LOGO_TEXT = "SmartMonitoring by btc."


class ConfigDefaults:
    # Default values for the local config file
    LOG_FILE_SIZE_LIMIT_MB = 50 # Max size of the log file in MB
    LOG_FILE_COUNT_LIMIT = 3 # Max number of log files
    ENABLE_DEBUG_LOGGING = False # Enable debug logging
    UPDATE_CHANNEL = "stable" # Update channel