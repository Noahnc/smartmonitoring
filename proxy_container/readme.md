# Zabbix Proxy Docker Image

This folder contains all files related to the modified Zabbix Proxy Docker Image.

- SNMP MIB files that need to be available in the Zabbix Proxy can be added to the `src/snmp_mibs` folder.
- External Scripts can be added to the `src/external_scripts` folder. Supported are bash or python scripts.
- The Dockerfile also installs python3.9 and all dependencies specified in the `requirements.txt` file.

The following Command builds a new image for x86 and arm64v8:
````
docker buildx build --platform linux/amd64,linux/arm64 -t btcadmin/smartmonitoring_proxy:<zabbix-version>-<revision-number> --push .
````
Version for the image should be set as following: `<zabbix-version>-<revision-number>`
whereas "zabbix-version" is the Zabbix release (e.g 6.2) and "revision-number" being an increasing number.

The following example builds an image for Zabbix 6.0 with revision number 01:
````
docker buildx build --platform linux/amd64,linux/arm64 -t noahnc/smartmonitoring-proxy:6.0-01 --push .
````

To update to a new Zabbix Proxy Version, the following line in the Dockerfile has to be changed to the new version:
````
FROM zabbix/zabbix-proxy-mysql:6.0-ubuntu-latest
````
The available Version-Tags can be found on the Zabbix Docker Hub page:
https://hub.docker.com/r/zabbix/zabbix-proxy-mysql