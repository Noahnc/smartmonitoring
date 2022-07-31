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
varSmartMonitoringConfigFilePath="$varSmartMonitoringConfFolder/smartmonitoring_config.yaml"
varZabbixPSKFilePath="$varSmartMonitoringConfFolder/psk_key.txt"

# Auffangen des Shell Terminator
trap ctrl_c INT

function ctrl_c() {
    echo ""
    echo -e "\e[31mAusführung des Script wurde abgebrochen.\e[39m"

    if [[ $ScriptFolderPath = *"$ProjectFolderName" ]]; then
        rm -r "$ScriptFolderPath"
    fi
    exit 1
}

function OK() {
    echo -e "\e[32m$1\e[39m"
}

function error() {
    echo -e "\e[31m
Fehler beim ausführen des Scripts, folgender Vorgang ist fehlgeschlagen:
$1
Bitte prüfe den Log-Output.\e[39m"
    if [[ $ScriptFolderPath = *"$ProjectFolderName" ]]; then
        rm -r "$ScriptFolderPath"
    fi
    exit 1
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

    # Neu erstellte Banner ausführbar machen
    chmod a+x /etc/update-motd.d/* || error "Fehler beim einrichten des Login Banners"

    OK "Login Banner wurde erfolgreich erstellt"
}

function CreateFolder() {
    if [[ ! -d "$1" ]]; then
        mkdir -p "$1" || error "Fehler beim erstellen des Ordners $1"
        OK "Ordner $1 wurde erstellt"
    fi
}

function InstallProgramm() {
if ! [ -x "$(command -v $1)" ]; then
    apt-get install $1 -y || error "Fehler beim installieren von $1"
    OK "$1 erfolgreich installiert"
else
    OK "$1 ist auf diesem System bereits installiert"
fi
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

timedatectl set-timezone Europe/Zurich

CreateFolder "$varSmartMonitoringConfFolder"
CreateFolder "$varSmartMonitoringvarFolder"
CreateFolder "$varSmartMonitoringLogFolder"


InstallProgramm "docker.io"
InstallProgramm "$PythonVersion"

# OK "SmartMonitoring wird deployed... "
# smartmonitoring deploy -s
# if [[ $? -ne 0 ]]; then
#     error "Fehler beim deployen der SmartMonitoring Container"
# fi
# OK "SmartMonitoring wurde erfolgreich deployed"


cat >$varZabbixPSKFilePath <<EOF
$varPSKKey
EOF
OK "PSK Key für Zabbix Proxy gespeichert"

cat >$varSmartMonitoringConfigFilePath <<EOF
SmartMonitoring_Proxy:
  #update_channel: STABLE # STABLE / TESTING
  #debug_logging: true # Logs as debug if true
  #log_file_size_mb: 50 #size of a single log file
  #log_file_count: 3 #amount of log files for rotation
  update_manifest_url: $varManifestUrl

  zabbix_proxy_container:
    proxy_name: $varProxyName
    psk_key_file: /Users/noahcanadea/Dev/zabbix_enc_key.psk

    # Bei Local settings können lokale einstellungen für den Container übersteuert werden.
    # Ist die gleiche Variable auch im manifest definiert, hat diese hier immer vorrang.
    #local_settings:
      #ZBX_DEBUGEVEL: 3

  zabbix_agent_container:
    smartmonitoring_status_file: "/Users/noahcanadea/Documents/GitHub/smartmonitoring/smartmonitoring/temp/update-status.json"

    #local_settings:

  #zabbix_mysql_container:
    #local_settings:
EOF

cat >/etc/cron.hourly/smartmonitoring <<EOF
#!/bin/bash
/usr/local/bin/smartmonitoring update -s
EOF
chmod +x /etc/cron.hourly/smartmonitoring
OK "Cron job erstellt"

CreateLoginBanner || error "Fehler beim erstellen des Login Banners"

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
Public iP:\e[33m $varMyPublicIP\e[34m
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