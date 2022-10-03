import logging as lg
import os
import socket
import requests


def delete_file_if_exists(filename) -> None:
    if os.path.exists(filename):
        lg.debug("Deleting file: " + str(filename))
        try:
            os.remove(filename)
        except Exception as e:
            lg.warning("Error deleting file: " +
                       str(filename) + " - " + str(e))
            raise e
    else:
        lg.debug("File does not exist: " + str(filename))


def create_folder_if_not_exists(folder: os.path) -> None:
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except Exception as e:
            raise e


def get_local_ip_address() -> str:
    """
    Evaluates the local ip address of the device by connecting to google dns
    :return: String of the local ip address
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except Exception as e:
        lg.debug("Error getting local ip address: " + str(e))
        return "unknown"


def get_public_ip_address() -> str:
    """
    Evaluates the public ip address of the device by connecting a public ip address service
    :return: Public ip address as string
    """
    import requests
    try:
        public_ip = requests.get('https://checkip.amazonaws.com').text.strip()
    except Exception as e:
        lg.debug("Error getting public ip address: " + str(e))
        public_ip = "unknown"
    return public_ip


def check_internet_connection() -> bool:
    """
    Checks if the device is connected to the internet by connecting to different services
    :return: True if one of the services is reachable, False if not
    """
    if check_server_connection("https://www.google.com"):
        return True
    elif check_server_connection("https://www.bing.com"):
        return True
    elif check_server_connection("https://www.yahoo.com"):
        return True
    else:
        lg.debug("No internet connection detected")
        return False


def check_server_connection(url: str) -> bool:
    """
    Check if the specified url is reachable
    :param url: URL to check
    :return: True if reachable, False if not
    """
    try:
        requests.get(url, timeout=4)
        lg.debug(f'Connection to {url} successful')
        return True
    except Exception as e:
        lg.debug(f'Error connecting to: {url} - {e}')
        return False
