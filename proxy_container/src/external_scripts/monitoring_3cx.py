#!/usr/bin/env python3

########################################################################
#                   Copyright © by Noah Canadea
########################################################################
#                           Description
#    Python script to get all kind of metrics from a 3cx server api
#
#                    Version 1.0 | 11.04.2022


# import dependencies
from argparse import ArgumentParser
import json
import socket
import requests
import sys
from dataclasses import dataclass
from typing import List, Union, Any, TypeVar, Callable, Type, cast, Optional
from datetime import datetime
import dateutil.parser

# Config variables
VERSION = "1.0"
MIN_PYTHON_VERSION = (3, 10) # python version 3.9 or higher is required

# global variables
base_url_3cx = None
username = None
password = None
domain = None
tcp_port = None
scriptHealthCheck = False
debugMode = False
auth_cookie = None
session = requests.Session()


################################################ Models ################################################

T = TypeVar("T")

def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x

def from_none(x: Any) -> Any:
    assert x is None
    return x

def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x

def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)

def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()

def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)

def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x

def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False

@dataclass
class Service:
    name: str
    display_name: str
    status: int
    memory_used: int
    cpu_usage: int
    thread_count: int
    handle_count: int
    start_stop_enabled: bool
    restart_enabled: bool

    @staticmethod
    def from_dict(obj: Any) -> 'Service':
        assert isinstance(obj, dict)
        name = from_str(obj.get("Name"))
        display_name = from_str(obj.get("DisplayName"))
        status = from_int(obj.get("Status"))
        memory_used = from_int(obj.get("MemoryUsed"))
        cpu_usage = from_int(obj.get("CpuUsage"))
        thread_count = from_int(obj.get("ThreadCount"))
        handle_count = from_int(obj.get("HandleCount"))
        start_stop_enabled = from_bool(obj.get("startStopEnabled"))
        restart_enabled = from_bool(obj.get("restartEnabled"))
        return Service(name, display_name, status, memory_used, cpu_usage, thread_count, handle_count, start_stop_enabled, restart_enabled)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Name"] = from_str(self.name)
        result["DisplayName"] = from_str(self.display_name)
        result["Status"] = from_int(self.status)
        result["MemoryUsed"] = from_int(self.memory_used)
        result["CpuUsage"] = from_int(self.cpu_usage)
        result["ThreadCount"] = from_int(self.thread_count)
        result["HandleCount"] = from_int(self.handle_count)
        result["startStopEnabled"] = from_bool(self.start_stop_enabled)
        result["restartEnabled"] = from_bool(self.restart_enabled)
        return result
    
    
@dataclass
class SystemStatus:
    fqdn: str
    web_meeting_fqdn: str
    version: str
    recording_state: int
    activated: bool
    max_sim_calls: int
    max_sim_meeting_participants: int
    call_history_count: int
    chat_messages_count: int
    extensions_registered: int
    own_push: bool
    ip: str
    ip_v4: str
    ip_v6: str
    local_ip_valid: bool
    current_local_ip: str
    available_local_ips: str
    extensions_total: int
    has_unregistered_system_extensions: bool
    has_not_running_services: bool
    trunks_registered: int
    trunks_total: int
    calls_active: int
    blacklisted_ip_count: int
    memory_usage: int
    physical_memory_usage: int
    free_virtual_memory: int
    total_virtual_memory: int
    free_physical_memory: int
    total_physical_memory: int
    disk_usage: int
    free_disk_space: int
    total_disk_space: int
    cpu_usage: int
    cpu_usage_history: List[List[Union[datetime, float]]]
    maintenance_expires_at: datetime
    support: bool
    license_active: bool
    expiration_date: datetime
    outbound_rules: int
    backup_scheduled: bool
    last_backup_date_time: datetime
    reseller_name: str
    license_key: str
    product_code: str
    is_audit_log_enabled: bool
    is_spla: bool

    @staticmethod
    def from_dict(obj: Any) -> 'SystemStatus':
        assert isinstance(obj, dict)
        fqdn = from_str(obj.get("FQDN"))
        web_meeting_fqdn = from_str(obj.get("WebMeetingFQDN"))
        version = from_str(obj.get("Version"))
        recording_state = from_int(obj.get("RecordingState"))
        activated = from_bool(obj.get("Activated"))
        max_sim_calls = from_int(obj.get("MaxSimCalls"))
        max_sim_meeting_participants = from_int(obj.get("MaxSimMeetingParticipants"))
        call_history_count = from_int(obj.get("CallHistoryCount"))
        chat_messages_count = from_int(obj.get("ChatMessagesCount"))
        extensions_registered = from_int(obj.get("ExtensionsRegistered"))
        own_push = from_bool(obj.get("OwnPush"))
        ip = from_str(obj.get("Ip"))
        ip_v4 = from_str(obj.get("IpV4"))
        ip_v6 = from_str(obj.get("IpV6"))
        local_ip_valid = from_bool(obj.get("LocalIpValid"))
        current_local_ip = from_str(obj.get("CurrentLocalIp"))
        available_local_ips = from_str(obj.get("AvailableLocalIps"))
        extensions_total = from_int(obj.get("ExtensionsTotal"))
        has_unregistered_system_extensions = from_bool(obj.get("HasUnregisteredSystemExtensions"))
        has_not_running_services = from_bool(obj.get("HasNotRunningServices"))
        trunks_registered = from_int(obj.get("TrunksRegistered"))
        trunks_total = from_int(obj.get("TrunksTotal"))
        calls_active = from_int(obj.get("CallsActive"))
        blacklisted_ip_count = from_int(obj.get("BlacklistedIpCount"))
        memory_usage = from_int(obj.get("MemoryUsage"))
        physical_memory_usage = from_int(obj.get("PhysicalMemoryUsage"))
        free_virtual_memory = from_int(obj.get("FreeVirtualMemory"))
        total_virtual_memory = from_int(obj.get("TotalVirtualMemory"))
        free_physical_memory = from_int(obj.get("FreePhysicalMemory"))
        total_physical_memory = from_int(obj.get("TotalPhysicalMemory"))
        disk_usage = from_int(obj.get("DiskUsage"))
        free_disk_space = from_int(obj.get("FreeDiskSpace"))
        total_disk_space = from_int(obj.get("TotalDiskSpace"))
        cpu_usage = from_int(obj.get("CpuUsage"))
        cpu_usage_history = from_list(lambda x: from_list(lambda x: from_union([from_float, from_datetime], x), x), obj.get("CpuUsageHistory"))
        maintenance_expires_at = from_datetime(obj.get("MaintenanceExpiresAt"))
        support = from_bool(obj.get("Support"))
        license_active = from_bool(obj.get("LicenseActive"))
        expiration_date = from_datetime(obj.get("ExpirationDate"))
        outbound_rules = from_int(obj.get("OutboundRules"))
        backup_scheduled = from_bool(obj.get("BackupScheduled"))
        last_backup_date_time = from_datetime(obj.get("LastBackupDateTime"))
        reseller_name = from_str(obj.get("ResellerName"))
        license_key = from_str(obj.get("LicenseKey"))
        product_code = from_str(obj.get("ProductCode"))
        is_audit_log_enabled = from_bool(obj.get("IsAuditLogEnabled"))
        is_spla = from_bool(obj.get("IsSpla"))
        return SystemStatus(fqdn, web_meeting_fqdn, version, recording_state, activated, max_sim_calls, max_sim_meeting_participants, call_history_count, chat_messages_count, extensions_registered, own_push, ip, ip_v4, ip_v6, local_ip_valid, current_local_ip, available_local_ips, extensions_total, has_unregistered_system_extensions, has_not_running_services, trunks_registered, trunks_total, calls_active, blacklisted_ip_count, memory_usage, physical_memory_usage, free_virtual_memory, total_virtual_memory, free_physical_memory, total_physical_memory, disk_usage, free_disk_space, total_disk_space, cpu_usage, cpu_usage_history, maintenance_expires_at, support, license_active, expiration_date, outbound_rules, backup_scheduled, last_backup_date_time, reseller_name, license_key, product_code, is_audit_log_enabled, is_spla)

    def to_dict(self) -> dict:
        result: dict = {}
        result["FQDN"] = from_str(self.fqdn)
        result["WebMeetingFQDN"] = from_str(self.web_meeting_fqdn)
        result["Version"] = from_str(self.version)
        result["RecordingState"] = from_int(self.recording_state)
        result["Activated"] = from_bool(self.activated)
        result["MaxSimCalls"] = from_int(self.max_sim_calls)
        result["MaxSimMeetingParticipants"] = from_int(self.max_sim_meeting_participants)
        result["CallHistoryCount"] = from_int(self.call_history_count)
        result["ChatMessagesCount"] = from_int(self.chat_messages_count)
        result["ExtensionsRegistered"] = from_int(self.extensions_registered)
        result["OwnPush"] = from_bool(self.own_push)
        result["Ip"] = from_str(self.ip)
        result["IpV4"] = from_str(self.ip_v4)
        result["IpV6"] = from_str(self.ip_v6)
        result["LocalIpValid"] = from_bool(self.local_ip_valid)
        result["CurrentLocalIp"] = from_str(self.current_local_ip)
        result["AvailableLocalIps"] = from_str(self.available_local_ips)
        result["ExtensionsTotal"] = from_int(self.extensions_total)
        result["HasUnregisteredSystemExtensions"] = from_bool(self.has_unregistered_system_extensions)
        result["HasNotRunningServices"] = from_bool(self.has_not_running_services)
        result["TrunksRegistered"] = from_int(self.trunks_registered)
        result["TrunksTotal"] = from_int(self.trunks_total)
        result["CallsActive"] = from_int(self.calls_active)
        result["BlacklistedIpCount"] = from_int(self.blacklisted_ip_count)
        result["MemoryUsage"] = from_int(self.memory_usage)
        result["PhysicalMemoryUsage"] = from_int(self.physical_memory_usage)
        result["FreeVirtualMemory"] = from_int(self.free_virtual_memory)
        result["TotalVirtualMemory"] = from_int(self.total_virtual_memory)
        result["FreePhysicalMemory"] = from_int(self.free_physical_memory)
        result["TotalPhysicalMemory"] = from_int(self.total_physical_memory)
        result["DiskUsage"] = from_int(self.disk_usage)
        result["FreeDiskSpace"] = from_int(self.free_disk_space)
        result["TotalDiskSpace"] = from_int(self.total_disk_space)
        result["CpuUsage"] = from_int(self.cpu_usage)
        result["CpuUsageHistory"] = from_list(lambda x: from_list(lambda x: from_union([to_float, lambda x: x.isoformat()], x), x), self.cpu_usage_history)
        result["MaintenanceExpiresAt"] = self.maintenance_expires_at.isoformat()
        result["Support"] = from_bool(self.support)
        result["LicenseActive"] = from_bool(self.license_active)
        result["ExpirationDate"] = self.expiration_date.isoformat()
        result["OutboundRules"] = from_int(self.outbound_rules)
        result["BackupScheduled"] = from_bool(self.backup_scheduled)
        result["LastBackupDateTime"] = self.last_backup_date_time.isoformat()
        result["ResellerName"] = from_str(self.reseller_name)
        result["LicenseKey"] = from_str(self.license_key)
        result["ProductCode"] = from_str(self.product_code)
        result["IsAuditLogEnabled"] = from_bool(self.is_audit_log_enabled)
        result["IsSpla"] = from_bool(self.is_spla)
        return result
    
    
@dataclass
class TrunkStatus:
    status: bool
    time: str
    agents: int
    calls: int

    @staticmethod
    def from_dict(obj: Any) -> 'TrunkStatus':
        assert isinstance(obj, dict)
        status = from_bool(obj.get("Status"))
        time = from_str(obj.get("Time"))
        agents = int(from_str(obj.get("Agents")))
        calls = from_int(obj.get("Calls"))
        return TrunkStatus(status, time, agents, calls)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Status"] = from_bool(self.status)
        result["Time"] = from_str(self.time)
        result["Agents"] = from_str(str(self.agents))
        result["Calls"] = from_int(self.calls)
        return result

@dataclass
class Trunk:
    id: str
    number: str
    name: str
    host: str
    type: str
    sim_calls: int
    external_number: str
    register_ok_time: str
    register_sent_time: str
    register_failed_time: str
    can_be_deleted: bool
    is_registered: Optional[bool] = None
    is_expired_provider_root_certificate: Optional[bool] = None
    expired_provider_root_certificate_date: Optional[str] = None
    audio_port: Optional[int] = None
    log_file_size: Optional[int] = None
    security: Optional[int] = None
    log_level: Optional[int] = None
    passive_server_is_enabled: Optional[bool] = None
    passive_server: Optional[str] = None
    sbc_id: Optional[int] = None
    password: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
    provision_link: Optional[str] = None
    public_ip: Optional[str] = None
    local_ip: Optional[str] = None
    version: Optional[str] = None
    secure: Optional[bool] = None
    os: Optional[str] = None
    out_of_date: Optional[bool] = None
    status: Optional[TrunkStatus] = None
    legacy: Optional[bool] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Trunk':
        assert isinstance(obj, dict)
        id = from_str(obj.get("Id"))
        number = from_str(obj.get("Number"))
        name = from_str(obj.get("Name"))
        host = from_str(obj.get("Host"))
        type = from_str(obj.get("Type"))
        sim_calls = from_union([from_int, lambda x: int(from_str(x))], obj.get("SimCalls"))
        external_number = from_str(obj.get("ExternalNumber"))
        register_ok_time = from_str(obj.get("RegisterOkTime"))
        register_sent_time = from_str(obj.get("RegisterSentTime"))
        register_failed_time = from_str(obj.get("RegisterFailedTime"))
        can_be_deleted = from_bool(obj.get("CanBeDeleted"))
        is_registered = from_union([from_bool, from_none], obj.get("IsRegistered"))
        is_expired_provider_root_certificate = from_union([from_bool, from_none], obj.get("IsExpiredProviderRootCertificate"))
        expired_provider_root_certificate_date = from_union([from_str, from_none], obj.get("ExpiredProviderRootCertificateDate"))
        audio_port = from_union([from_int, from_none], obj.get("AudioPort"))
        log_file_size = from_union([from_int, from_none], obj.get("LogFileSize"))
        security = from_union([from_int, from_none], obj.get("Security"))
        log_level = from_union([from_int, from_none], obj.get("LogLevel"))
        passive_server_is_enabled = from_union([from_bool, from_none], obj.get("PassiveServerIsEnabled"))
        passive_server = from_union([from_str, from_none], obj.get("PassiveServer"))
        sbc_id = from_union([from_int, from_none], obj.get("SbcId"))
        password = from_union([from_str, from_none], obj.get("Password"))
        description = from_union([from_str, from_none], obj.get("Description"))
        link = from_union([from_str, from_none], obj.get("Link"))
        provision_link = from_union([from_str, from_none], obj.get("ProvisionLink"))
        public_ip = from_union([from_str, from_none], obj.get("PublicIP"))
        local_ip = from_union([from_str, from_none], obj.get("LocalIP"))
        version = from_union([from_str, from_none], obj.get("Version"))
        secure = from_union([from_bool, from_none], obj.get("Secure"))
        os = from_union([from_str, from_none], obj.get("OS"))
        out_of_date = from_union([from_bool, from_none], obj.get("OutOfDate"))
        status = from_union([TrunkStatus.from_dict, from_none], obj.get("Status"))
        legacy = from_union([from_bool, from_none], obj.get("Legacy"))
        return Trunk(id, number, name, host, type, sim_calls, external_number, register_ok_time, register_sent_time, register_failed_time, can_be_deleted, is_registered, is_expired_provider_root_certificate, expired_provider_root_certificate_date, audio_port, log_file_size, security, log_level, passive_server_is_enabled, passive_server, sbc_id, password, description, link, provision_link, public_ip, local_ip, version, secure, os, out_of_date, status, legacy)

    def to_dict(self) -> dict:
        result: dict = {}
        result["Id"] = from_str(self.id)
        result["Number"] = from_str(self.number)
        result["Name"] = from_str(self.name)
        result["Host"] = from_str(self.host)
        result["Type"] = from_str(self.type)
        result["SimCalls"] = from_int(self.sim_calls)
        result["ExternalNumber"] = from_str(self.external_number)
        result["RegisterOkTime"] = from_str(self.register_ok_time)
        result["RegisterSentTime"] = from_str(self.register_sent_time)
        result["RegisterFailedTime"] = from_str(self.register_failed_time)
        result["CanBeDeleted"] = from_bool(self.can_be_deleted)
        result["IsRegistered"] = from_union([from_bool, from_none], self.is_registered)
        result["IsExpiredProviderRootCertificate"] = from_union([from_bool, from_none], self.is_expired_provider_root_certificate)
        result["ExpiredProviderRootCertificateDate"] = from_union([from_str, from_none], self.expired_provider_root_certificate_date)
        result["AudioPort"] = from_union([from_int, from_none], self.audio_port)
        result["LogFileSize"] = from_union([from_int, from_none], self.log_file_size)
        result["Security"] = from_union([from_int, from_none], self.security)
        result["LogLevel"] = from_union([from_int, from_none], self.log_level)
        result["PassiveServerIsEnabled"] = from_union([from_bool, from_none], self.passive_server_is_enabled)
        result["PassiveServer"] = from_union([from_str, from_none], self.passive_server)
        result["SbcId"] = from_union([from_int, from_none], self.sbc_id)
        result["Password"] = from_union([from_str, from_none], self.password)
        result["Description"] = from_union([from_str, from_none], self.description)
        result["Link"] = from_union([from_str, from_none], self.link)
        result["ProvisionLink"] = from_union([from_str, from_none], self.provision_link)
        result["PublicIP"] = from_union([from_str, from_none], self.public_ip)
        result["LocalIP"] = from_union([from_str, from_none], self.local_ip)
        result["Version"] = from_union([from_str, from_none], self.version)
        result["Secure"] = from_union([from_bool, from_none], self.secure)
        result["OS"] = from_union([from_str, from_none], self.os)
        result["OutOfDate"] = from_union([from_bool, from_none], self.out_of_date)
        result["Status"] = from_union([lambda x: to_class(Status, x), from_none], self.status)
        result["Legacy"] = from_union([from_bool, from_none], self.legacy)
        return result


@dataclass
class Trunks:
    list: List[Trunk]
    is_refresh_trunks_registration_prohibited: bool
    is_licence_standard: bool

    @staticmethod
    def from_dict(obj: Any) -> 'Trunks':
        assert isinstance(obj, dict)
        list = from_list(Trunk.from_dict, obj.get("list"))
        is_refresh_trunks_registration_prohibited = from_bool(obj.get("isRefreshTrunksRegistrationProhibited"))
        is_licence_standard = from_bool(obj.get("isLicenceStandard"))
        return Trunks(list, is_refresh_trunks_registration_prohibited, is_licence_standard)

    def to_dict(self) -> dict:
        result: dict = {}
        result["list"] = from_list(lambda x: to_class(Trunk, x), self.list)
        result["isRefreshTrunksRegistrationProhibited"] = from_bool(self.is_refresh_trunks_registration_prohibited)
        result["isLicenceStandard"] = from_bool(self.is_licence_standard)
        return result
    
    
################################################ Script Entry ################################################

def main():
    # global script variables
    global base_url_3cx
    global username
    global password
    global scriptHealthCheck
    global debugMode
    global domain
    global tcp_port

    # exit if python version is too old
    if sys.version_info < MIN_PYTHON_VERSION:
        exitScript(1, "Python version is too old", sys.version_info)

    # getting all arguments
    parser = ArgumentParser(
        description='Zabbix script 3CX monitoring.', add_help=True)
    parser.add_argument('-u', '--username', default='btcadmin',
                        type=str, help='Username to connect with')
    parser.add_argument('-p', '--password', default='btcadmin',
                        type=str, help='Password for the username')
    parser.add_argument('-d', '--domain', type=str,
                        help='Domain of the 3cx server')
    parser.add_argument('-t', '--tcpport', default=443, type=int,
                        help='TCP Port of the 3cx server WebUI')
    parser.add_argument('-c', '--category', type=str,
                        help='The category of the values which should be returned')
    parser.add_argument('--debug', type=bool, default=False,
                        help='prints more information when a error occurs')
    parser.add_argument('--discovery', type=bool,
                        help='flag to set in zabbix discovery mode')  # is not really used in the script itself, but since zabbix requires each item to have a unique key, this is used for the discovery rule
    parser.add_argument('-v', '--version', action='version',
                        version=VERSION, help='Print script version and exit')

    # pharse arguments
    args = parser.parse_args()

    # check if all required arguments are set and exit if not
    if args.username is None or args.password is None or args.domain is None or args.category is None:
        parser.print_help()
        exitScript(1, "Not all required arguments provided", None)

    # set global variables
    username = args.username
    password = args.password
    domain = args.domain
    tcp_port = args.tcpport
    debugMode = args.debug

    # set base url based on https port
    if args.tcpport != 443:
        base_url_3cx = f'https://{args.domain}:{args.tcpport}/api/'
    else:
        base_url_3cx = f'https://{args.domain}/api/'

    # call ScriptHealtCheck if specified in category-argument
    if args.category == "script-health-check":
        scriptHealthCheck = True
        ScriptHealtCheck()
    else:
        checkPortAndExitOnError(domain, tcp_port) # check if port is open before trying to connect to 3cx api
        print(getJsonOfCategory(args.category))

# function that calculates the percentage between two values
def calculatePercentage(used, total) -> float:
    if total == 0:
        return 0
    else:
        return round((used / total) * 100, 2)

# function that takes a category and returns all values of that category as json string
def getJsonOfCategory(category) -> str:
    if category == "3cx-status":
        values = get3CXSystemStatus()
        dic = {
            "FreeMem": values.free_physical_memory,
            "TotalMem": values.total_physical_memory,
            "MemoryUsedPercent": calculatePercentage((values.total_physical_memory - values.free_physical_memory), values.total_physical_memory),
            "CpuUtil": values.cpu_usage,
            "DiskUsedPercent": calculatePercentage((values.total_disk_space - values.free_disk_space), values.total_disk_space),
            "TrunkTot": values.trunks_total,
            "TrunkReg": values.trunks_registered,
            "LicenseActive": values.license_active,
            "CallsActive": values.calls_active,
            "IpBlockCount": values.blacklisted_ip_count,
            "ip_address": values.ip_v4

        }
    elif category == "3cx-info":
        values = get3CXSystemStatus()
        dic = {
            "Autobackup": values.backup_scheduled,
            "LicCode": values.license_key,
            "InstVersion": values.version,
            "LicenseExpireDateUnix": values.expiration_date.timestamp(),
            "3CXFQDN": values.fqdn

        }
    elif category == "3cx-services":
        dic = []
        services = get3CXServices()
        for service in services:
            temp_dic = {
                "name": service.name,
                "status": service.status
            }
            dic.append(temp_dic)
    elif category == "3cx-trunks":
        dic = []
        trunks = get3CXTrunks().list
        for trunk in trunks:
            if trunk.type == "Provider":
                temp_dic = {
                    "name": trunk.name,
                    "registered": trunk.is_registered,
                }
                dic.append(temp_dic)
    elif category == "3cx-sbc":
        dic = []
        trunks = get3CXTrunks().list
        for trunk in trunks:
            if trunk.type == "SBC":
                temp_dic = {
                    "name": trunk.name,
                    "registered": True if trunk.status.status == False else False,
                    "OutOfDate": trunk.out_of_date
                }
                dic.append(temp_dic)
    else:
            # exit script if no valid category is given
            exitScript(1, "Invalid category argument specified", category)
    try:
        # parse dic to json and exit on error
        return json.dumps(dic, separators=(',', ':'), default=str)
    except Exception as e:
        exitScript(1, "error while creating json string", e)

# function to get all 3cx services as services object and return it
def get3CXServices() -> Service:
    response = getDataFrom3CXAPI('ServiceList')
    try:
        data = from_list(Service.from_dict, json.loads(response))
    except Exception as e:
        exitScript(1, "3CX Services parse error", e)
    return data

# function to get all 3cx trunks as list in an object and return it
def get3CXTrunks() -> Trunks:
    response = getDataFrom3CXAPI('TrunkList')
    try:
        data = Trunks.from_dict(json.loads(response))
    except Exception as e:
        exitScript(1, "3CX Trunks parse error", e)
    return data

# function to get 3cx status as object and return it
def get3CXSystemStatus() -> SystemStatus:
    response = getDataFrom3CXAPI('SystemStatus')
    try:
        data = SystemStatus.from_dict(json.loads(response))
    except Exception as e:
        exitScript(1, "3CX SystemStatus parse error", e)
    return data

# function that gets the data from the 3cx api on a specific recourse url
def getDataFrom3CXAPI(uri) -> str:
    if auth_cookie is None: APIauthentication() # get auth cookie if not already available
    try:
        url = base_url_3cx + uri
        headers = {'content-type': 'application/json;charset=UTF-8'}
        response = session.get(url, headers=headers, cookies=auth_cookie)
    except Exception as e:
        exitScript(1, "Error while connecting to 3cx api on recourse: " + uri, e)
    return response.text

# function that gets the access cookie from 3cx api
def APIauthentication() -> None:
    global auth_cookie
    url = base_url_3cx + 'login'
    payload = {'username': username, 'password': password}
    headers = {'content-type': 'application/json'}
    try:
        response = session.post(url, data=json.dumps(
            payload).encode('utf-8'), headers=headers)
    except Exception as e:
        exitScript(1, "Error while connecting to 3cx server api", e)
    if response.status_code == 200 and response.text == 'AuthSuccess':
        auth_cookie = response.cookies
    else:
        exitScript(1, "API authentication error", response.text)

# function to test all components of the script and return the status to the zabbix healthcheck item
def ScriptHealtCheck() -> None:
    # check if port is open and exit with error if not
    checkPortAndExitOnError(domain, tcp_port)

    # get all data from 3cx api and parse to models
    # if any error occurs, the script will be terminated with basic healthcheck error message, which is shown in the zabbix healthcheck item
    testjson1 = getJsonOfCategory("3cx-status")
    testjson2 = getJsonOfCategory("3cx-info")
    testjson3 = getJsonOfCategory("3cx-services")
    testjson4 = getJsonOfCategory("3cx-trunks")

    # if no exception occurred, the script will be terminated with healthcheck OK
    exitScript(0, "OK", "Script test successful, everything works fine")

# checks if the specified port is open on the remote host and exits the script if not
def checkPortAndExitOnError(host: str, port: int) -> None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        return True
    except Exception as e:
        exitScript(1, "Can't connect to " + host + " on Port " + str(port), e)

# function to exit the script with a specific exit code and message
# errors are only printed, if the script is executed in debug mode or as healthcheck
# healthcheck only prints basic information, while debug mode prints all information
def exitScript(exitCode: int, message: str, info) -> None:
    if scriptHealthCheck and debugMode == False: print(message)
    if debugMode:
        print(message + ": ")
        print(info)
    if exitCode != 0 and debugMode:
        raise
    exit(exitCode)

# call main function if script is executed as main
if __name__ == '__main__':
    main()
    