#!/bin/bash

########################################################################
#         Copyright © by Noah Canadea | All rights reserved
########################################################################
#                           Description
#       Bash Script to setup a smartmonitoring proxy server
#
#                    Version 1.0 | 19.08.2022

# Global config variables
var_python_version="Python3.9"
var_smartmonitoring_download_url="https://github.com/Noahnc/smartmonitoring/releases/download/0.6.2/smartmonitoring-0.6.2.tar.gz"
var_smartmonitoring_update_manifest_url="https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/manifest.yaml"

var_psk_identity="PSK_KEY"
var_smartmonitoring_file_name="smartmonitoring.tar.gz"
var_psk_key=$(openssl rand -hex 512)
var_smartmonitoring_config_folder="/etc/smartmonitoring"
var_smartmonitoring_var_folder="/var/smartmonitoring"
var_smartmonitoring_log_folder="/var/log/smartmonitoring"
var_install_log_file="$var_smartmonitoring_log_folder/install.log"
var_smartmonitoring_config_file_path="$var_smartmonitoring_config_folder/smartmonitoring_config.yaml"
var_psk_file_path="$var_smartmonitoring_config_folder/psk_key.txt"

# Catch shell termination
trap ctrl_c INT

function ctrl_c() {
    echo ""
    echo -e "\e[31mInstallation manually terminated.\e[39m"
    exit 2
}

function error() {
    # Delete downloaded smartmonitoring sdist file
    DeleteFile "$var_smartmonitoring_file_name"
    echo -e "\e[31m
A critical error occurred during installation of SmartMonitoring.
Please check the following log file for more information:\e[39m
Logfile: $var_install_log_file"
    exit 1
}

# function to delete a file
function delete_file() {
    if [ -f "$1" ]; then
        echo "Deleting file: $1"
        rm -f "$1"
    fi
}
# clears the last line that was printed to console
function clear_last_line() {
    tput cuu 1 && tput el
}
# replaces last line with OK
function confirm_task_ok() {
    clear_last_line
    echo -e "\e[32m[ OK ]\e[39m $1"
}
# replaces last line with Error
function task_error() {
    clear_last_line
    echo -e "\e[31m[ ERROR ]\e[39m $1"
    error "$1"
}

# prints that a task has started
function start_task() {
    echo -e "\e[36m[ RUNNING ]\e[39m $1"
}

# create and log folder
function create_folder() {
    if [[ ! -d "$1" ]]; then
      echo "Creating folder $1"
        mkdir -p "$1"
    fi
}

# installs a program form apt with accept flag -y
function install_program() {
    if ! [ -x "$(command -v "$1")" ]; then
        apt-get install "$1" -y
    fi
}

# function that takes a command and a description
# runs the command and shows the current status (running, finished or failed)
function perform_operation() {
    command=$1
    name=$2
    start_task "$name"
    $command &>>$var_install_log_file || task_error "$name"
    confirm_task_ok "$name"
}

# function that sets the login banner
function create_login_banner() {
    # Delete some not needed default banners from ubuntu
    delete_file "/etc/motd"
    delete_file "/etc/update-motd.d/10-uname"
    delete_file "/etc/update-motd.d/20-hints"
    delete_file "/etc/update-motd.d/50-banner"
    delete_file "/etc/update-motd.d/50-landscape-sysinfo"
    delete_file "/etc/update-motd.d/50-motd-news"
    delete_file "/etc/update-motd.d/88-esm-announce"

    # Create new motd file
    cat >/etc/update-motd.d/00-smartmonitoring <<EOF
#!/bin/bash
smartmonitoring status --disable-refresh        
EOF
    # Make the file executable
    chmod a+x /etc/update-motd.d/*
}

function create_folders() {
    # Create SmartMonitoring folders
    create_folder "$var_smartmonitoring_log_folder"
    create_folder "$var_smartmonitoring_config_folder"
    create_folder "$var_smartmonitoring_var_folder"
}

# generates and saves the smartmonitoring local config file
function save_smartmonitoring_files() {
    cat >$var_smartmonitoring_config_file_path <<EOF
SmartMonitoring_Proxy:
  update_channel: STABLE # STABLE / TESTING
  #debug_logging: true # Logs as debug if true
  #log_file_size_mb: 50 #size of a single log file
  #log_file_count: 3 #amount of log files for rotation
  update_manifest_url: "$var_smartmonitoring_update_manifest_url"

  zabbix_proxy_container:
    proxy_name: $var_proxy_name
    psk_key_file: "$var_psk_file_path"

    # With local settings, you can override static configurations from the manifest.
    # A variable specified here takes precedence over the one from the manifest.
    #local_settings:
      #ZBX_DEBUGEVEL: 3

  zabbix_agent_container:
    smartmonitoring_status_file: "/var/smartmonitoring/update-status.json"

    #local_settings:

  #zabbix_mysql_container:
    #local_settings:
EOF

# Save Zabbix PSK key
echo "$var_psk_key" >"$var_psk_file_path"
}


function print_logo() {
    echo -e " \e[34m
             _____     _     _     _         _              _     _         
            |__  /__ _| |__ | |__ (_)_  __  | |__  _   _   | |__ | |_ ___   
              / // _  | '_ \| '_ \| \ \/ /  | '_ \| | | |  | '_ \| __/ __|  
             / /| (_| | |_) | |_) | |>  <   | |_) | |_| |  | |_) | || (__ _ 
            /____\__,_|_.__/|_.__/|_/_/\_\  |_.__/ \__, |  |_.__/ \__\___(_)
                                                   |___/
____________________________________________________________________________________________

\e[39m
"
}

# Print finish text with required information
function print_finish_text() {
    print_logo
    echo -e " \e[34m
Installation of SmartMonitoring successfully completed.
Please create this proxy in the Zabbix WebPortal with the following information:

Proxy Name:\e[33m $var_proxy_name\e[34m
PSK Identity:\e[33m $var_psk_identity\e[34m
256bit PSK Key:\e[33m
$var_psk_key\e[34m

Also create the following host object in Zabbix:

Host name:\e[33m $var_proxy_name\e[34m
Groups:\e[33m Device_Zabbix-proxys\e[34m
Templates:\e[33m btc SmartMonitoring Proxy\e[34m
Interface Agent:\e[33m zabbix-agent2-container\e[34m
\e[39m
"
}

# creates a hourly running cron job
function create_cron_job() {
    cat >/etc/cron.hourly/smartmonitoring <<EOF
#!/bin/bash
/usr/local/bin/smartmonitoring update -s
EOF
    chmod +x /etc/cron.hourly/smartmonitoring
}

# downloads and installs smartmonitoring sdist package
function install_smartmonitoring() {
    wget $var_smartmonitoring_download_url -O $var_smartmonitoring_file_name
    pip install $var_smartmonitoring_file_name
}

# sets different ubuntu settings
function set_ubuntu_settings(){
    # Set Timezone
    timedatectl set-timezone Europe/Zurich
}

########################################## Script entry point ################################################

print_logo
echo -e " \e[34m
This is the setup script for btc SmartMonitoring Proxy's.
Please make sure, that the following conditions are met:
- NTP Traffic is allowed to the Internet.
- Traffic on TCP 10051 is allowed to the Internet.
- Traffic on TCP/UDP 443 is allowed to the Internet.

This script can be terminated any time with Ctrl+C.

\e[39m
"

# Check if executed on Ubuntu Linux and if not, exit.
if ! [[ -f /etc/lsb-release ]]; then
    error "SmartMonitoring Proxys can only be installed on Ubuntu Linux."
fi

# Check if executed as root and exit if not.
# shellcheck disable=SC2004
if (($EUID != 0)); then
    error "Pleas run this script with root privileges."
fi

# Check if smartmonitoring is already installed.
if ! [[ -f "/usr/local/bin/smartmonitoring" ]]; then

    ############################ Perform new installation ############################

    # Ask for Customer Name by CLI input
    var_location=
    var_customer_name=
    var_content_valid="false"
    while [[ $var_content_valid = "false" ]]; do
        echo "Please enter the name of the customer. E.G. MusterAG (Allowed characters: a-z A-Z 0-9 _ )"
        read -r -e -p "Company: " -i "$var_customer_name" var_customer_name
        if ! [[ $var_customer_name =~ [^a-zA-Z0-9_-] ]]; then
            var_content_valid="true"
        else
            echo -e "\e[31mInvalid Input provided!\e[39m"
        fi
    done

    # Ask for Customer Location by CLI input
    var_content_valid="false"
    while [[ $var_content_valid = "false" ]]; do
        echo "Please enter the location of the customer. E.G. Daettwil (Allowed characters: a-z A-Z 0-9 _ )"
        read -r -e -p "$var_customer_name-Proxy-" -i "$var_location" var_location
        if ! [[ $var_location =~ [^a-zA-Z0-9_] ]]; then
            var_content_valid="true"
        else
            echo -e "\e[31mInvalid Input provided!\e[39m"
        fi
    done

    # Compose Zabbix Proxy Name from Customer Name and Location
    var_proxy_name="$var_customer_name-Proxy-$var_location"

    # Start installation tasks
    echo ""
    echo "################################ Perform Installation ############################################"
    create_folders
    perform_operation "set_ubuntu_settings" "Set Ubuntu settings..."
    perform_operation "apt-get update" "Update apt cache..."

    perform_operation "install_program docker.io" "Installing Docker Engine..."
    perform_operation "install_program $var_python_version" "Installing $var_python_version..."
    perform_operation "install_program python3-pip" "Installing pip..."
    perform_operation "install_smartmonitoring" "Installing SmartMonitoring Updater package..."

    perform_operation "save_smartmonitoring_files $var_smartmonitoring_update_manifest_url $var_proxy_name $var_psk_file_path" "Saving SmartMonitoring Files..."
    perform_operation "create_cron_job" "Create Cron Job for auto-update..."
    perform_operation "create_login_banner" "Create Login Banner..."
    perform_operation "smartmonitoring deploy -s -v" "Deploying SmartMonitoring..."

    print_finish_text
else
  # Ask if smartmonitoring tool should be updated
    var_content_valid="false"
    while [[ $var_content_valid = "false" ]]; do
        echo "SmartMonitoring is already installed on this system."
        read -r -p "Do you want to update? (y/n): " var_choice
        if [[ $var_choice == "n" ]]; then
            echo "Update of SmartMonitoring canceled!"
            exit 0
        elif [[ $var_choice == "y" ]]; then
            var_content_valid="true"
        else
            echo -e "\e[31mInput not valid!\e[39m"
        fi
    done

    echo ""
    echo "################################## Perform Update ##################################"
    perform_operation "smartmonitoring undeploy -s -v" "Remove current SmartMonitoring Deployment..."
    perform_operation "install_smartmonitoring" "Installing new Version of SmartMonitoring Updater..."
    perform_operation "smartmonitoring deploy -s -v" "Deploy SmartMonitoring..."
    echo "Update finished!"
fi
########################################## Script end ################################################
# delete downloaded file
delete_file "$var_smartmonitoring_file_name" &>>$var_install_log_file
