import logging as lg
import os
import sys

import click
from rich.console import Console

import smartmonitoring_cli.helpers.log_helper as lh
from smartmonitoring_cli.main_logic import MainLogic


@click.group()
def main():
    if sys.platform.startswith("linux"):
        if os.geteuid() != 0:
            print("You need to have root privileges to run this application.")
            print("Please try again, this time using 'sudo'.")
            sys.exit(1)


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in silent mode, which writes all output to the log file")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def restart(silent: bool, verbose: bool):
    """Restarts all Containers of the current deployment."""
    main_logic = prepare_cli("Restarting all containers of deployment...", verbose, silent)
    command_executer(verbose, silent, main_logic.restart_application)


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def validate_config(verbose: bool):
    """Validates the local config for errors in the syntax."""
    main_logic = prepare_cli("Applying new local config", verbose, False, True)
    command_executer(verbose, False, main_logic.check_configurations, verbose)


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in silent mode, which writes all output to the log file")
def apply_config(verbose: bool, silent: bool):
    """Validates the local config file and applies it if valid."""
    main_logic = prepare_cli("Applying new local config", verbose, silent)
    command_executer(verbose, silent, main_logic.validate_and_apply_config, silent)


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in silent mode, which writes all output to the log file")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def deploy(silent: bool, verbose: bool):
    """Deploys SmartMonitoring on this System."""
    main_logic = prepare_cli("Deploying SmartMonitoring", verbose, silent)
    command_executer(verbose, silent, main_logic.deploy_application)


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in silent mode, which writes all output to the log file")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def undeploy(silent: bool, verbose: bool):
    """Removes the SmartMonitoring Deployment from this system."""
    main_logic = prepare_cli("Removing SmartMonitoring deployment", verbose, silent)
    command_executer(verbose, silent, main_logic.remove_application)


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in silent mode, which writes all output to the log file")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
@click.option("-f", "--force", is_flag=True, default=False,
              help="Applies the remote manifest even if it is not newer than the local one")
def update(silent: bool, verbose: bool, force: bool):
    """Checks if a newer SmartMonitoring Deployment is available and updates it if so."""
    main_logic = prepare_cli("Updating SmartMonitoring deployment", verbose, silent)
    command_executer(verbose, silent, main_logic.update_application, force)


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
@click.option("--disable-refresh", is_flag=True, default=False, help="Disables automatic refresh of the Dashboard")
@click.option("--banner-version", is_flag=True, default=False,
              help="Prints reduced information for the shell login banner")
def status(verbose: bool, disable_refresh: bool, banner_version: bool):
    """Shows a status dashboard with important metrics."""
    if verbose: disable_refresh = True
    main_logic = prepare_cli("Showing status dashboard", verbose, False, only_critical=True)
    command_executer(verbose, False, main_logic.print_status, disable_refresh, banner_version)


def exit_with_error(code: int) -> None:
    lg.critical(f'Exiting with error code {code} because of an critical error.')
    exit(code)


def prepare_cli(action: str, verbose: bool, silent: bool, only_critical: bool = False) -> MainLogic:
    main_logic = MainLogic()
    command_executer(verbose, silent, main_logic.setup_logging, verbose, silent, only_critical)
    lh.log_start(action)
    return main_logic


def command_executer(verbose: bool, silent: bool, function, *args) -> None:
    try:
        function(*args)
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected, exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        if verbose and not silent:
            Console().print_exception(show_locals=True)
        elif verbose and silent:
            lg.debug(f'Stack trace: ', exc_info=True)
        else:
            lg.info('Run the command with the --verbose flag to get more information.')
        exit_with_error(1)
    finally:
        lh.log_finish()
