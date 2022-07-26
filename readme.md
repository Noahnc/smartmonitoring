# SmartMonitoring
This repository contains all files associated with the SmartMonitoring project.
SmartMonitoring is a deployment solution for Zabbix Proxy's.
A Zabbix Proxy Deployment is defined in an update manifest file that is publicly available over the internet.
To update configuration or Zabbix version for all Proxy's, you can change the update manifest and therefore update all Proxy's at once.

# Folder Structure
- `proxy_container`: Contains all files to build the modified Zabbix Proxy Docker Image
- `smartmonitoring-cli`: Contains all Source Code and other files regarding SmartMonitoring-CLI

## Installation of SmartMonitoring-CLI
SmartMonitoring-CLI can be installed with the following command:
````
wget -qO - https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/install.sh | bash <(cat) </dev/tty <smartmonitoring-cli_version>
````
The version-number has to be a valid release from the releases page.
Example for version 0.7.0:
````
wget -qO - https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/install.sh | bash <(cat) </dev/tty 0.7.0
````
After SmartMonitoring-CLI and all it's dependencies got installed successfully, SmartMonitoring-CLI automatically performs the initial deployment.

## Available Commands
Apply a modified local config:
````
smartmonitoring apply-config <--verbose> <--silent>
````
![](https://github.com/Noahnc/smartmonitoring/blob/release/asset/apply-config.gif)

\
Shows a Dashboard with usefully information about the Host and the current Deployment:
````
smartmonitoring status <--verbose> <--disable-refresh> <--banner-version>
````
![](https://github.com/Noahnc/smartmonitoring/blob/release/asset/status-dashboard.gif)

\
Checks if a new SmartMonitoring Deployment is available and deploys it if so:
````
smartmonitoring update <--verbose> <--silent> <--force>
````
![](https://github.com/Noahnc/smartmonitoring/blob/release/asset/update.gif)

\
Checks the local config file and the manifest for errors:
````
smartmonitoring validate-config <--verbose>
````
![](https://github.com/Noahnc/smartmonitoring/blob/release/asset/validate-config.gif)
\
The following command perform an initial deployment based on the manifest:
````
smartmonitoring deply <--verbose> <--silent>
````
\
This command removes an active deployment completely:
````
smartmonitoring undeploy <--verbose> <--silent>
````
\
Restart all containers of the current deployment:
````
smartmonitoring restart <--verbose> <--silent>
````

