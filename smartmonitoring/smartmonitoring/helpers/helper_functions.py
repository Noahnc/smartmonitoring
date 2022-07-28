import logging as lg
import os


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

def check_for_duplicates(list_of_items: list) -> bool:
    return len(list_of_items) != len(set(list_of_items))


def exit_with_error(code: int) -> None:
    lg.critical(f'Exiting with error code {code} because of an critical error.')
    exit(code)


def get_public_ip_address() -> str:
    import requests
    try:
        public_ip = requests.get('https://checkip.amazonaws.com').text.strip()
    except Exception as e:
        lg.debug("Error getting public ip address: " + str(e))
        public_ip = "unknown"
    return public_ip
