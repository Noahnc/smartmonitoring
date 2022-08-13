from rich.console import Console
from rich.prompt import Confirm

import smartmonitoring.const_settings as cs
from pyfiglet import Figlet


def print_logo() -> None:
    f = Figlet(font='standard', width=cs.CLI_WIDTH, justify='center')
    print(f.renderText(cs.CLI_LOGO_TEXT))


def print_paragraph(text: str) -> None:
    print(f' {text} '.center(cs.CLI_WIDTH + 5, "-"))


def print_and_confirm_changes(changes: str) -> bool:
    print_paragraph("The following changes were found in the configuration")
    Console().print(changes)
    return Confirm.ask("Do you want to apply these changes?")
