# SmartMonitoring
In this repository are all files associated with the SmartMonitoring project.
# Folder Structure
- `proxy_container`: Contains all files to build the modified Zabbix Proxy Docker Image
- `smartmonitoring-cli`: Contains all Source Code and other files regarding SmartMonitoring-CLI
## Installation of SmartMonitoring-CLI
SmartMonitoring-CLI can be installed with the following command:
````
wget -qO - https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/install.sh | bash <(cat) </dev/tty <smartmonitoring-cli_version>
````
The version-number has to be a valid release version from the releases page.
Example for version 0.7.0:
````
wget -qO - https://storage.googleapis.com/btc-public-accessible-data/smartmonitoring_proxies/install.sh | bash <(cat) </dev/tty 0.7.0
````
SmartMonitoring-CLI and all it's dependencies got installed successfully, SmartMonitoring-CLI automatically performs the initial deployment.

## Available Commands
The following command perform an initial deployment based on the manifest:
````
smartmonitoring deply <--verbose> <--silent>
````
This command removes an active deployment completely:
````
smartmonitoring undeploy <--verbose> <--silent>
````
Apply a modified local config:
````
smartmonitoring apply-config <--verbose> <--silent>
````
Restart all containers of the current deployment:
````
smartmonitoring restart-config <--verbose> <--silent>
````
Shows a Dashboard with usefully information about the Host and the current Deployment:
````
smartmonitoring status <--verbose> <--disable-refresh> <--banner-version>
````
![](https://github.com/noahnc/smartmonitoring/asset/status-dashboard.gif)
Checks if a new SmartMonitoring Deployment is available and deploys it if so:
````
smartmonitoring update <--verbose> <--silent> <--force>
````
Checks the local config file and the manifest for errors:
````
smartmonitoring validate-config <--verbose>
````