import const_settings as cs
from pyfiglet import Figlet
import textwrap

from termcolor import colored

class cli_colors:
    BLUE = '\x1b[38;5;39m'
    RED = '\x1b[38;5;196m'
    GREEN = '\x1b[38;5;46m'
    RESET = '\x1b[0m'
    
def print_success(message: str) -> None:
    print(cli_colors.GREEN + message + cli_colors.RESET)

def print_error(message: str) -> None:
    print(cli_colors.RED + message + cli_colors.RESET)
    
def print_information(message: str) -> None:
    print(cli_colors.BLUE + message + cli_colors.RESET)   
    
def print_paragraph(text: str) -> None:
    print(f' {text} '.center(cs.CLI_WIDTH, "-"))
    
def print_logo() -> None:
    f = Figlet(font='standard', width=cs.CLI_WIDTH + 10, justify='center')
    print(f.renderText(cs.CLI_LOGO_TEXT))

def print_centered_text(label: str, value:str, color:cli_colors = None) -> None:
    print(cli_colors.BLUE + str(label).center(cs.CLI_WIDTH) + cli_colors.RESET)
    texts = textwrap.wrap(str(value), cs.CLI_WIDTH - 10)
    for text in texts:
        if color is not None:
            print(color + text.center(cs.CLI_WIDTH) + cli_colors.RESET)
        else:
            print(text.center(cs.CLI_WIDTH))
    print()
    
def print_and_confirm_changes(changes: str) -> bool:
    print_paragraph("The following changes were found in the configuration")
    print(changes)
    return get_user_confirm("Do you want to apply these changes? (y/n): ")
    
def get_user_confirm(message:str) -> bool:
    while True:
        answer = input(message)
        if answer.lower() in ['y', 'yes']:
            return True
        elif answer.lower() in ['n', 'no']:
            return False
        else:
            print("Please answer with 'y' or 'n'.")


