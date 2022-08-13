# Zabbix Proxy Docker Image

In this folder are all the necessary files to build a SmartMonitoring Proxy Docker Image.

- SNMP MIB files that need to be available in the Zabbix Proxy can be added to the `src/snmp_mibs` folder.
- External Scripts can be added to the `src/external:scripts` folder. Supported are bash or python scripts.
- The Dockerfile also installs python3.9 and all dependencies specified in the `requirements.txt` file.

The following Command builds a new image for x86 and arm (make sure you are in the current folder when running the command):
````
docker buildx build --platform linux/amd64,linux/arm64 -t noahnc/smartmonitoring-proxy:<zabbix-version>-<revision-number> --push .
````

The following example builds an image for Zabbix 6.0 with revision number 01:
````
docker buildx build --platform linux/amd64,linux/arm64 -t noahnc/smartmonitoring-proxy:6.0-01 --push .
````

To update to a new Zabbix Proxy Version, the following line in the Dockerfile has to be changed to the new version:
````
FROM zabbix/zabbix-proxy-mysql:6.0-ubuntu-latest
````
The available Version-Tags can be found on the Zabbix Docker Hub Page:
https://hub.docker.com/r/zabbix/zabbix-proxy-mysql