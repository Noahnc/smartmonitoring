import platform
import socket
import time
from multiprocessing import Pool

import psutil
from pyfiglet import Figlet
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm
from rich.table import Table

import smartmonitoring_cli.const_settings as cs
import smartmonitoring_cli.helpers.helper_functions as hf
from smartmonitoring_cli import __version__
from smartmonitoring_cli.handlers.data_handler import DataHandler
from smartmonitoring_cli.handlers.docker_handler import DockerHandler
from smartmonitoring_cli.models.local_config import LocalConfig
from smartmonitoring_cli.models.update_manifest import UpdateManifest, ContainerConfig


def print_logo() -> None:
    """Prints the SmartMonitoring logo"""
    f = Figlet(font='standard', width=cs.CLI_WIDTH, justify='center')
    print(f.renderText(cs.CLI_LOGO_TEXT))


def print_paragraph(text: str) -> None:
    """
    Prints a paragraph with the given text
    :param text: Text in the paragraph
    """
    print(f' {text} '.center(cs.CLI_WIDTH + 5, "-"))


def print_and_confirm_changes(changes: str) -> bool:
    """
    Prints a string of changes and asks the user to confirm them
    :param changes: String of changes
    :return: True if users confirms, False otherwise
    """
    print_paragraph("The following changes were found in the configuration")
    Console().print(changes)
    return Confirm.ask("Do you want to apply these changes?")


def print_system_status(cfh: DataHandler, config: LocalConfig = None, manifest: UpdateManifest = None) -> None:
    """
    Prints a table with information about the system and deployment status
    :param cfh: A DataHandler instance
    :param config: LocalConfig object
    :param manifest: Manifest object
    """
    if config is None or manifest is None:
        status = "Not deployed"
        version = "-"
        channel = "-"
        proxy_name = "-"
    else:
        status = cfh.get_status()["status"]
        version = manifest.package_version
        channel = config.update_channel
        proxy_name = config.zabbix_proxy_container.proxy_name
    table = Table(width=cs.CLI_WIDTH,
                  title="System and Deployment Status",
                  show_header=False)
    table.add_column("Host Information", justify="center", width=cs.CLI_WIDTH)
    table.add_column("Deployment Status", justify="center", width=cs.CLI_WIDTH)
    table.add_row("[bright_cyan]System Hostname", "[bright_cyan]Deployment Status")
    table.add_row(socket.gethostname(), "[green]Deployed" if status == "Deployed" else "[red]Not deployed")
    table.add_row()
    table.add_row("[bright_cyan]SmartMonitoring-CLI Version", "[bright_cyan]Package Deployment Version")
    table.add_row(__version__, version)
    table.add_row()
    table.add_row("[bright_cyan]Local IP Address", "[bright_cyan]Update Channel")
    table.add_row(hf.get_local_ip_address(), channel)
    table.add_row()
    table.add_row("[bright_cyan]Public IP Address", "[bright_cyan]Proxy Name")
    table.add_row(hf.get_public_ip_address(), proxy_name)

    Console().print(table)


def __generate_container_table(initializing: bool, containers: list[ContainerConfig] = None) -> Table:
    """
    Generates a table with information about the containers of the current deployment
    :param initializing: Should be true on the first call of this function to initialize the table
    :param containers: List of ContainerConfig objects for which the table should be generated
    :return: Returns a Table object with the container information
    """
    table = Table(width=cs.CLI_WIDTH, title="Container Statistics")
    if containers is None:
        table.add_column("[bright_cyan]SmartMonitoring not deployed, skipping container statistics...",
                         justify="center")
        table.box = None
        return table
    if initializing:
        table.add_column("Loading containers...", justify="center")
        table.box = None
        return table
    table.add_column("Name", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Image", justify="center")
    table.add_column("Memory Usage", justify="center")
    table.add_column("CPU Usage", justify="center")
    cont_stats = __get_container_statistics_parallel(containers)
    for cont_stat in cont_stats:
        table.add_row(f'{cont_stat["name"]}', f'{cont_stat["status"]}', f'{cont_stat["image"]}',
                      f'{cont_stat["mem_usg_mb"]}', f'{cont_stat["cpu_usg_present"]}')
    return table


def __generate_host_information_table() -> Table:
    """
    Generates a table with information about the host system
    :return: Returns a Table object with the host information
    """
    table = Table(width=cs.CLI_WIDTH,
                  title="Host Information",
                  show_header=False)
    table.add_column("Row 1", justify="center", width=cs.CLI_WIDTH)
    table.add_column("Row 2", justify="center", width=cs.CLI_WIDTH)
    table.add_column("Row 3", justify="center", width=cs.CLI_WIDTH)
    table.add_row("[bright_cyan]OS", "[bright_cyan]CPU Usage", "[bright_cyan]CPU Core Count")
    table.add_row(platform.platform(), f'{psutil.cpu_percent()} %', f'{psutil.cpu_count()}')
    table.add_row()
    table.add_row("[bright_cyan]Disk Space Total",
                  "[bright_cyan]Disk Space Free",
                  "[bright_cyan]Disk Usage Percent")
    table.add_row(f'{round(psutil.disk_usage("/").total / 1073741824, 2)} GB',
                  f'{round(psutil.disk_usage("/").free / 1073741824, 2)} GB',
                  f'{psutil.disk_usage("/").percent} %')
    table.add_row()
    table.add_row("[bright_cyan]Memory Total",
                  "[bright_cyan]Memory Free",
                  "[bright_cyan]Memory Usage Percent")
    table.add_row(f'{round(psutil.virtual_memory().total / 1073741824, 2)} GB',
                  f'{round(psutil.virtual_memory().available / 1073741824, 2)} GB',
                  f'{psutil.virtual_memory().percent} %')
    return table


def __get_container_statistics_parallel(conf_containers: list[ContainerConfig]) -> list[dict]:
    """
    Gets the container statistics for all containers in the current deployment in parallel
    :param conf_containers: List of ContainerConfig objects for which the statistics should be retrieved
    :return: List of dictionaries with the container statistics
    """
    with Pool(len(conf_containers)) as p:
        container_stats = p.map(get_container_stats_process, iter(conf_containers))
    return container_stats


def get_container_stats_process(container_config: ContainerConfig) -> dict:
    """
    Gets the container statistics for a single container
    :param container_config: ContainerConfig object for which the statistics should be retrieved
    :return: Dictionary with the container statistics
    """
    dock = DockerHandler()
    return dock.get_container_stats(container_config)


def print_live_updating_tables(disable_refresh: bool, containers: list = None) -> None:
    """
    Prints the host information and container statistics tables in a loop
    :param disable_refresh: Only print the tables once if true
    :param containers: ContainerConfig objects for which the container statistics should be printed
    """
    if disable_refresh:
        runs = 1
    else:
        runs = 100
    try:
        with Live(__compose_live_tables(True, containers), auto_refresh=False) as live:
            for run in range(runs):
                live.update(__compose_live_tables(False, containers), refresh=True)
                time.sleep(2)
        if not disable_refresh: print("Timeout reached, exiting...")
    except KeyboardInterrupt:
        print("Exit Status Dashboard".center(cs.CLI_WIDTH))


def __compose_live_tables(initialize: bool, containers: list[ContainerConfig] = None) -> Table.grid:
    """
    Composes the host information and container statistics tables into a grid
    :param initialize: Should be True for the first call to initialize the container table
    :param containers: ContainerConfig objects for which the container statistics should be printed
    :return: A Table grid object with the host information and container statistics tables
    """
    grid = Table.grid()
    grid.add_column()
    grid.add_row(__generate_host_information_table())
    grid.add_row(__generate_container_table(initialize, containers))
    grid.add_row("Press Ctrl+C to exit")
    return grid


def print_logon_banner(config: LocalConfig = None, manifest: UpdateManifest = None) -> None:
    """
    Prints a reduced status dashboard for log-in banners
    :param config: Configuration object for the current deployment
    :param manifest: Update manifest object for the current deployment
    """
    if config is None or manifest is None:
        status = "Not deployed"
        version = "-"
        channel = "-"
    else:
        status = "Deployed"
        version = manifest.package_version
        channel = config.update_channel
    print("".center(cs.CLI_WIDTH - 10, "-"))
    grid = Table.grid(collapse_padding=False)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_column(justify="center")
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row("Deployment Status: ", status, "        ", "Hostname: ", socket.gethostname())
    grid.add_row("Package Version: ", version, "        ", "Local IP: ", hf.get_local_ip_address())
    grid.add_row("Update Channel: ", channel, "         ", "Public IP: ", hf.get_public_ip_address())
    Console().print(grid)
