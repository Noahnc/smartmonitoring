#!/bin/bash

########################################################################
#         Copyright © by Noah Canadea | All rights reserved
########################################################################
#                           Description
#       Bash Script to setup a smartmonitoring proxy server
#
#                    Version 1.0 | 21.07.2022


# Global variables
PythonVersion="Python3.9"
Script_setup_directory="$(dirname -- "$0")"
varPSKidentity="PSK_KEY"
Script_src_directory="$(dirname "$Script_setup_directory")"
ScriptFolderPath="$(dirname "$Script_src_directory")"
ProjectFolderName="SmartMonitoring_Proxy"                                                                                
varSmartMonitorFolder="SmartMonitor"
varPSKKey=$(openssl rand -hex 512)
varContentValid=
varProxyName=
varManifestUrl=$1
varSmartMonitoringConfFolder="/etc/smartmonitoring"
varSmartMonitoringvarFolder="/var/smartmonitoring"
varSmartMonitoringLogFolder="/var/log/smartmonitoring"
varIntallerLogFile="$varSmartMonitoringLogFolder/install.log"
varSmartMonitoringConfigFilePath="$varSmartMonitoringConfFolder/smartmonitoring_config.yaml"
varZabbixPSKFilePath="$varSmartMonitoringConfFolder/psk_key.txt"

# Auffangen des Shell Terminator
trap ctrl_c INT

function ctrl_c() {
    echo ""
    echo -e "\e[31mInstall manually terminated.\e[39m"
    exit 2
}


function error() {
    echo -e "\e[31m
A critical error occured during installation of SmartMonitoring.
Please check the following log file for more information:\e[39m
$varIntallerLogFile"
    exit 1
}

function clearLastLine() {
    tput cuu 1 && tput el
}

function confirm_task_ok(){
    clearLastLine
    echo -e "\e[32m[ OK ]\e[39m $1" 
}

function task_error(){
    clearLastLine
    echo -e "\e[31m[ ERROR ]\e[39m $1"
}

function start_task(){
    echo "[ RUNNING ] $1"
}


function CreateLoginBanner() {

    if [[ -f /etc/motd ]]; then
        rm -f /etc/motd
    fi

    if [[ -f /etc/update-motd.d/10-uname ]]; then
        rm /etc/update-motd.d/10-uname
    fi

    if [[ -f /etc/update-motd.d/50-landscape-sysinfo ]]; then
        rm /etc/update-motd.d/50-landscape-sysinfo
    fi

    # Erstelle das Logo
    cat >/etc/update-motd.d/00-smartmonitoring <<EOF
#!/bin/bash
smartmonitoring status --disable-refresh        
EOF

    
    chmod a+x /etc/update-motd.d/*
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
    $comand &>> $varIntallerLogFile || error "$name"
    confirm_task_ok "$name"
}

function CreateFolders() {
    CreateFolder "$varSmartMonitoringLogFolder"
    CreateFolder "$varSmartMonitoringConfFolder"
    CreateFolder "$varSmartMonitoringvarFolder"
}

function SavePSKKey() {
    echo "$varPSKKey" > "$varZabbixPSKFilePath"
}

function SaveSmartMonitoringConfig(){
    cat >$varSmartMonitoringConfigFilePath <<EOF
SmartMonitoring_Proxy:
  #update_channel: STABLE # STABLE / TESTING
  #debug_logging: true # Logs as debug if true
  #log_file_size_mb: 50 #size of a single log file
  #log_file_count: 3 #amount of log files for rotation
  update_manifest_url: $1

  zabbix_proxy_container:
    proxy_name: $2
    psk_key_file: /Users/noahcanadea/Dev/zabbix_enc_key.psk

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
}

function CreateCronJob() {
    cat >/etc/cron.hourly/smartmonitoring <<EOF
#!/bin/bash
/usr/local/bin/smartmonitoring update -s
EOF
    chmod +x /etc/cron.hourly/smartmonitoring
}


########################################## Script entry point ################################################

echo -e " \e[34m
             _____     _     _     _         _              _     _         
            |__  /__ _| |__ | |__ (_)_  __  | |__  _   _   | |__ | |_ ___   
              / // _  | '_ \| '_ \| \ \/ /  | '_ \| | | |  | '_ \| __/ __|  
             / /| (_| | |_) | |_) | |>  <   | |_) | |_| |  | |_) | || (__ _ 
            /____\__,_|_.__/|_.__/|_/_/\_\  |_.__/ \__, |  |_.__/ \__\___(_)
                                                   |___/
____________________________________________________________________________________________

Dies ist das Setup Script für btc SmartCollab Proxys.
Stelle sicher, dass folgende Bedingungen erfüllt sind:
- NTP Traffic ins Internet ist geöffnet.
- Port TCP 10051 ins Internet ist geöffnet.
- Port TCP/UDP 443 ins Internet ist geöffnet.

Du kannst die Ausführung dieses Scripts jederzeit mit Ctrl+C beenden.

\e[39m
"

# Prüfe ob das Script auf einem Ubuntu System ausgeführt wurde.
if ! [[ -f /etc/lsb-release ]]; then
    error "btc Zabbix Proxys dürfen nur auf Ubuntu Server installiert werden. Dieses System ist jedoch nicht kompatibel."
fi

# Aufnehmen des Kundennames
varLocation=
varCustomerName=
varContentValid="false"
while [[ $varContentValid = "false" ]]; do
    echo "Bitte den Namen des Kunden eingeben. Bspw. MusterAG (Erlaubte Zeichen: a-z A-Z 0-9 _ )"
    read -r -e -p "Firma: " -i "$varCustomerName" varCustomerName
    if ! [[ $varCustomerName =~ [^a-zA-Z0-9_-] ]]; then
        varContentValid="true"
    else
        echo -e "\e[31mKeine gültige Eingabe!\e[39m"
    fi
done

# Aufnehmen des Standorts
varContentValid="false"
while [[ $varContentValid = "false" ]]; do
    echo "Bitte den Namen des Standorts eintragen. Bspw. Daettwil (Erlaubte Zeichen: a-z A-Z 0-9 _ )"
    read -r -e -p "$varCustomerName-Proxy-" -i "$varLocation" varLocation
    if ! [[ $varLocation =~ [^a-zA-Z0-9_] ]]; then
        varContentValid="true"
    else
        echo -e "\e[31mKeine gültige Eingabe!\e[39m"
    fi
done

varProxyName="$varCustomerName-Proxy-$varLocation"

##################################### Start install tasks #####################################################
CreateFolders
PerformOperation "timedatectl set-timezone Europe/Zurich" "Set Timezone to Europe/Zurich"
PerformOperation "apt-get update" "Update apt repositories"

PerformOperation "InstallProgramm docker.io" "Install Docker Engine"
PerformOperation "InstallProgramm $PythonVersion" "Install $PythonVersion"


# OK "SmartMonitoring wird deployed... "
# smartmonitoring deploy -s
# if [[ $? -ne 0 ]]; then
#     error "Fehler beim deployen der SmartMonitoring Container"
# fi
# OK "SmartMonitoring wurde erfolgreich deployed"

PerformOperation "SavePSKKey" "Save Generated Zabbix PSK Key"

PerformOperation "SaveSmartMonitoringConfig $varUpdateManifestUrl $varProxyName" "Save SmartMonitoring Config"
PerformOperation "CreateCronJob" "Create Cron Job for auto update"
PerformOperation "CreateLoginBanner" "Create Login Banner"

echo -e " \e[34m
             _____     _     _     _         _              _     _         
            |__  /__ _| |__ | |__ (_)_  __  | |__  _   _   | |__ | |_ ___   
              / // _  | '_ \| '_ \| \ \/ /  | '_ \| | | |  | '_ \| __/ __|  
             / /| (_| | |_) | |_) | |>  <   | |_) | |_| |  | |_) | || (__ _ 
            /____\__,_|_.__/|_.__/|_/_/\_\  |_.__/ \__, |  |_.__/ \__\___(_)
                                                   |___/
____________________________________________________________________________________________

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
$varPSKKey\e[34m
"

########################################## Script end ################################################

# Löschen des Projekt Ordners
if [[ $ScriptFolderPath = *"$ProjectFolderName" ]]; then
    rm -r "$ScriptFolderPath"
fi