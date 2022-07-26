import sys
import logging as lg
import helpers.log_helpers as lh
from main_logic import MainLogic
import helpers.helper_functions as hf
import click


@click.group()
def main():
    pass


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in interactive mode")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def restart(silent: bool, verbose: bool):
    """Restarts all Containers of the current deployment."""
    try:
        main_logic = MainLogic()
        main_logic.setup_logging(verbose, silent)
        lh.log_start("Restarting all containers of deployment...")
        main_logic.restart_application()
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --verbose flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def validate_config(verbose: bool):
    """Validates the local config for errors in the syntax."""
    main_logic = MainLogic()
    if verbose: lh.add_console_logger(debug=verbose)
    try:
        main_logic.check_configurations(verbose)
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        if not verbose: lg.info('Run the application with the --verbose flag to get more information.')
        lg.debug(e, exc_info=True)
    pass


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in interactive mode")
def apply_config(verbose: bool, silent: bool):
    """Validates the local configuration file and applies it if valid."""
    try:
        main_logic = MainLogic()
        main_logic.setup_logging(verbose, False)
        lh.log_start("Applying local configuration file")
        main_logic.validate_and_apply_config(silent)
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --verbose flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in interactive mode")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def deploy(silent: bool, verbose: bool):
    """Deploys the SmartMonitoring Proxy Application on this System."""
    try:
        main_logic = MainLogic()
        main_logic.setup_logging(verbose, silent)
        lh.log_start("Deploying SmartMonitoring Proxy Application")
        main_logic.deploy_application()
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --verbose flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in interactive mode")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def undeploy(silent: bool, verbose: bool):
    """Removes the SmartMonitoring Application from this system."""
    try:
        main_logic = MainLogic()
        main_logic.setup_logging(verbose, silent)
        lh.log_start("Remove SmartMonitoring Proxy Application")
        main_logic.remove_application()
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --verbose flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()


@main.command()
@click.option("-s", "--silent", is_flag=True, default=False,
              help="Specify if you want to run the application in interactive mode")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
@click.option("-f", "--force", is_flag=True, default=False,
              help="Applies the remote manifest even if it is not newer than the local one")
def update(silent: bool, verbose: bool, force: bool):
    """Checks if a newer Version is available and updates the Application if so."""
    try:
        main_logic = MainLogic()
        main_logic.setup_logging(verbose, silent)
        lh.log_start("Updating SmartMonitoring Application")
        main_logic.update_application(force)
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --debug flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()


@main.command()
@click.option("-v", "--verbose", is_flag=True, default=False, help="Prints more information")
def status(verbose: bool):
    """Prints status information of the currently installed application stack."""
    try:
        main_logic = MainLogic()
        lh.add_console_logger(debug=verbose, level="ERROR")
        lh.log_start("Read and print status of Application")
        main_logic.print_status()
    except KeyboardInterrupt:
        lg.warning("KeyboardInterrupt detected. Exiting...")
    except Exception as e:
        lg.critical(f'Critical Error occurred: {e}')
        lg.debug(f'Stack trace: ', exc_info=True)
        if not verbose: lg.info('Run the application with the --debug flag to get more information.')
        hf.exit_with_error(1)
    finally:
        lh.log_finish()
