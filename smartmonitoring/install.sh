#!/bin/bash

########################################################################
#         Copyright © by Noah Canadea | All rights reserved
########################################################################
#                           Description
#       Bash Script to setup a smartmonitoring proxy server
#
#                    Version 1.0 | 21.07.2022

# Global config variables
varPythonVersion="Python3.9"
varSmartMonitoringDownloadURL="https://github.com/Noahnc/smartmonitoring/releases/download/alpha/smartmonitoring-0.5.0.tar.gz"
varSmartMonitoringManifestURL="https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/manifest.yaml"

varPSKidentity="PSK_KEY"
varSmartMonitoringFileName="smartmonitoring.tar.gz"
varPSKKey=$(openssl rand -hex 512)
varSmartMonitoringConfFolder="/etc/smartmonitoring"
varSmartMonitoringvarFolder="/var/smartmonitoring"
varSmartMonitoringLogFolder="/var/log/smartmonitoring"
varIntallerLogFile="$varSmartMonitoringLogFolder/install.log"
varSmartMonitoringConfigFilePath="$varSmartMonitoringConfFolder/smartmonitoring_config.yaml"
varZabbixPSKFilePath="$varSmartMonitoringConfFolder/psk_key.txt"

# Catch shell termination
trap ctrl_c INT

function ctrl_c() {
    echo ""
    echo -e "\e[31mInstall manually terminated.\e[39m"
    exit 2
}

function error() {
    DeleteFile "$varSmartMonitoringFileName"
    echo -e "\e[31m
A critical error occured during installation of SmartMonitoring.
Please check the following log file for more information:\e[39m
Logfile: $varIntallerLogFile"
    exit 1
}

function DeleteFile() {
    if [ -f "$1" ]; then
        echo "Deleting file: $1"
        rm -f "$1"
    fi
}

function ClearLastLine() {
    tput cuu 1 && tput el
}

function confirm_task_ok() {
    ClearLastLine
    echo -e "\e[32m[ OK ]\e[39m $1"
}

function task_error() {
    ClearLastLine
    echo -e "\e[31m[ ERROR ]\e[39m $1"
    error "$1"
}

function start_task() {
    echo "[ RUNNING ] $1"
}

function CreateFolder() {
    if [[ ! -d "$1" ]]; then
        mkdir -p "$1"
    fi
}

function InstallProgramm() {
    if ! [ -x "$(command -v $1)" ]; then
        apt-get install $1 -y
    fi
}

function PerformOperation() {
    comand=$1
    name=$2
    start_task "$name"
    $comand &>>$varIntallerLogFile || task_error "$name"
    confirm_task_ok "$name"
}

function CreateLoginBanner() {

    # Delete not needed motd files
    DeleteFile "/etc/motd"
    DeleteFile "/etc/update-motd.d/10-uname"
    DeleteFile "/etc/update-motd.d/20-hints"
    DeleteFile "/etc/update-motd.d/50-banner"
    DeleteFile "/etc/update-motd.d/50-landscape-sysinfo"
    DeleteFile "/etc/update-motd.d/50-motd-news"
    DeleteFile "/etc/update-motd.d/88-esm-announce"

    # Create new motd file
    cat >/etc/update-motd.d/00-smartmonitoring <<EOF
#!/bin/bash
smartmonitoring status --disable-refresh        
EOF
    # Make the file executable
    chmod a+x /etc/update-motd.d/*
}

function CreateFolders() {
    # Create SmartMonitoring foders
    CreateFolder "$varSmartMonitoringLogFolder"
    CreateFolder "$varSmartMonitoringConfFolder"
    CreateFolder "$varSmartMonitoringvarFolder"
}


function SaveSmartMonitoringFiles() {
    # Save config file
    cat >$varSmartMonitoringConfigFilePath <<EOF
SmartMonitoring_Proxy:
  update_channel: STABLE # STABLE / TESTING
  #debug_logging: true # Logs as debug if true
  #log_file_size_mb: 50 #size of a single log file
  #log_file_count: 3 #amount of log files for rotation
  update_manifest_url: "$SmartMonitoringManifestURL"

  zabbix_proxy_container:
    proxy_name: $varProxyName
    psk_key_file: "$varZabbixPSKFilePath"

    # Bei Local settings können lokale einstellungen für den Container übersteuert werden.
    # Ist die gleiche Variable auch im manifest definiert, hat diese hier immer vorrang.
    #local_settings:
      #ZBX_DEBUGEVEL: 3

  zabbix_agent_container:
    smartmonitoring_status_file: "/var/smartmonitoring/update-status.json"

    #local_settings:

  #zabbix_mysql_container:
    #local_settings:
EOF
# Save Zabbix PSK key
echo "$varPSKKey" >"$varZabbixPSKFilePath"
}

function PrintLogo() {
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

function PrintFinishText() {
    PrintLogo
    echo -e " \e[34m
Dein SmartMonitoring Proxy wurde erfolgreich Installiert!
Erstelle nun mit folgenden Angaben den Proxy im Zabbix WebPortal.

Proxy Name:\e[33m $varProxyName\e[34m
PSK Identity:\e[33m $varPSKidentity\e[34m
512bit PSK Key:\e[33m
$varPSKKey\e[34m

Erstelle ausserdem einen neuen Host mit folgenden Angaben:

Host name:\e[33m $varProxyName\e[34m
Groups:\e[33m Device_Zabbix-proxys\e[34m
Templates:\e[33m Zabbix-proxys\e[34m

____________________________________________________________________________________________

Trage ausserdem folgende Angaben im Keeper ein:

\e[34m
Titel:\e[33m Zabbix $varProxyName SSH Login\e[34m
Anmelden:\e[33m root\e[34m
Passwort:\e[33m $varRootPassword
\e[34m
Titel:\e[33m Zabbix Proxy $varProxyName PSK\e[34m
Anmelden:\e[33m $varPSKidentity\e[34m
Passwort:\e[33m
$varPSKKey\e[39m
"
}

function CreateCronJob() {
    cat >/etc/cron.hourly/smartmonitoring <<EOF
#!/bin/bash
/usr/local/bin/smartmonitoring update -s
EOF
    chmod +x /etc/cron.hourly/smartmonitoring
}

function InstallSmartMonitoring() {
    wget $varSmartMonitoringDownloadURL -O $varSmartMonitoringFileName
    pip install $varSmartMonitoringFileName
}

function SetUbuntuSettings(){
    # Set Timezone
    timedatectl set-timezone Europe/Zurich
}

########################################## Script entry point ################################################

PrintLogo
echo -e " \e[34m
This is the setup script for btc SmartMonitoring proxys.
Please make shure, that the following conditations are met:
- NTP Traffic is allowed to the Internet.
- Port TCP 10051 is open to the Internet.
- Port TCP/UDP 443 is Open to the Internet.

The script can be terminated any time with Ctrl+C.

\e[39m
"

# Check if executed on Ubuntu Linux.
if ! [[ -f /etc/lsb-release ]]; then
    error "SmartMonitoring Proxys can only be installed on Ubuntu Linux."
fi

# Check if executed as root.
if (($EUID != 0)); then
    error "Pleas run this script with root privileges."
fi

if ! [[ -f "/usr/local/bin/smartmonitoring" ]]; then

    ############################ Perform new installation ############################

    # Aufnehmen des Kundennames
    varLocation=
    varCustomerName=
    varContentValid="false"
    while [[ $varContentValid = "false" ]]; do
        echo "Please enter the name of the customer. E.G. MusterAG (Allowed characters: a-z A-Z 0-9 _ )"
        read -r -e -p "Firma: " -i "$varCustomerName" varCustomerName
        if ! [[ $varCustomerName =~ [^a-zA-Z0-9_-] ]]; then
            varContentValid="true"
        else
            echo -e "\e[31mInvalid Input provided!\e[39m"
        fi
    done

    # Aufnehmen des Standorts
    varContentValid="false"
    while [[ $varContentValid = "false" ]]; do
        echo "Please enter the location of the customer. E.G. Daettwil (Allowed characters: a-z A-Z 0-9 _ )"
        read -r -e -p "$varCustomerName-Proxy-" -i "$varLocation" varLocation
        if ! [[ $varLocation =~ [^a-zA-Z0-9_] ]]; then
            varContentValid="true"
        else
            echo -e "\e[31mInvalid Input provided!\e[39m"
        fi
    done

    varProxyName="$varCustomerName-Proxy-$varLocation"

    ##################################### Start install tasks #####################################################
    echo "\nPerforming SmartMonitoring Proxys installation..."
    CreateFolders
    PerformOperation "SetUbuntuSettings" "Set Ubuntu settings"
    PerformOperation "apt-get update" "Update apt cache"

    PerformOperation "InstallProgramm docker.io" "Install Docker Engine"
    PerformOperation "InstallProgramm $varPythonVersion" "Install $varPythonVersion"
    PerformOperation "InstallProgramm python3-pip" "Install pip"
    PerformOperation "InstallSmartMonitoring" "Install SmartMonitoring"

    PerformOperation "SaveSmartMonitoringFiles $varUpdateManifestUrl $varProxyName $varZabbixPSKFilePath" "Save SmartMonitoring Files"
    PerformOperation "CreateCronJob" "Create Cron Job for auto update"
    PerformOperation "CreateLoginBanner" "Create Login Banner"
    PerformOperation "smartmonitoring deploy -s -v" "Deploy SmartMonitoring"
else
    ############################ Perform update ############################
    varContentValid="false"
    while [[ $varContentValid = "false" ]]; do
        echo "SmartMonitoring is allready installed on this system."
        read -p "Do you want to update? (y/n): " varChoice
        if [[ $varChoice == "n" ]]; then
            echo "Update of SmartMonitoring cancled!"
            exit 0
        elif [[ $varChoice == "y" ]]; then
            varContentValid="true"
        else
            echo -e "\e[31mInput not valid!\e[39m"
        fi
    done

    PerformOperation "smartmonitoring undeploy -s -v" "Remove current SmartMonitoring Deployment"
    PerformOperation "InstallSmartMonitoring" "Installing new Version of SmartMonitoring"
    PerformOperation "smartmonitoring deploy -s -v" "Deploy SmartMonitoring"
    echo "Update finished!"
fi
########################################## Script end ################################################
DeleteFile "$varSmartMonitoringFileName"
