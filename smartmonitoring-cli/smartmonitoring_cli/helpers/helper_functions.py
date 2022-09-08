import logging as lg
import os
import socket


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
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except Exception as e:
        lg.debug("Error getting local ip address: " + str(e))
        return "unknown"


def get_public_ip_address() -> str:
    import requests
    try:
        public_ip = requests.get('https://checkip.amazonaws.com').text.strip()
    except Exception as e:
        lg.debug("Error getting public ip address: " + str(e))
        public_ip = "unknown"
    return public_ip
