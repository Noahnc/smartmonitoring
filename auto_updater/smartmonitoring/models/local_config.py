from dataclasses import dataclass
from typing import Dict, Optional, Any, Type, TypeVar, cast, Tuple

T = TypeVar("T")

def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False
    
def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x

def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x

def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class ZabbixMysqlContainer:
    local_settings: Optional[Dict] = None

    @staticmethod
    def from_dict(obj: Any) -> 'ZabbixMysqlContainer':
        assert isinstance(obj, dict)
        local_settings = obj.get("local_settings")
        return ZabbixMysqlContainer(local_settings)

    def to_dict(self) -> dict:
        result: dict = {}
        result["local_settings"] = self.local_settings
        return result

@dataclass
class ZabbixProxyContainer:
    proxy_name: str
    zabbix_server_psk: str
    psk_key_file: str
    local_settings: Optional[Dict] = None

    @staticmethod
    def from_dict(obj: Any) -> 'ZabbixProxyContainer':
        assert isinstance(obj, dict)
        proxy_name = from_str(obj.get("proxy_name"))
        zabbix_server_psk = from_str(obj.get("zabbix_server_psk"))
        psk_key_file = from_str(obj.get("psk_key_file"))
        local_settings = obj.get("local_settings")
        return ZabbixProxyContainer(proxy_name, zabbix_server_psk, psk_key_file, local_settings)

    def to_dict(self) -> dict:
        result: dict = {}
        result["proxy_name"] = from_str(self.proxy_name)
        result["zabbix_server_psk"] = from_str(self.zabbix_server_psk)
        result["psk_key_file"] = from_str(self.psk_key_file)
        result["local_settings"] = self.local_settings
        return result


@dataclass
class LocalConfig:
    update_channel: str
    debug_logging: bool
    log_file_size_mb: int
    log_file_count: int
    update_manifest_url: str
    zabbix_proxy_container: ZabbixProxyContainer
    zabbix_mysql_container: Optional[ZabbixMysqlContainer] = None

    @staticmethod
    def from_dict(obj: Any) -> 'LocalConfig':
        assert isinstance(obj, dict)
        update_channel = from_str(obj.get("update_channel"))
        debug_logging = from_bool(obj.get("debug_logging"))
        log_file_size_mb = from_int(obj.get("log_file_size_mb"))
        log_file_count = from_int(obj.get("log_file_count"))
        update_manifest_url = from_str(obj.get("update_manifest_url"))
        zabbix_proxy_container = ZabbixProxyContainer.from_dict(obj.get("zabbix_proxy_container"))
        zabbix_mysql_container = from_union([ZabbixMysqlContainer.from_dict, from_none], obj.get("zabbix_mysql_container"))
        return LocalConfig(update_channel, debug_logging, log_file_size_mb, log_file_count, update_manifest_url, zabbix_proxy_container, zabbix_mysql_container)

    def to_dict(self) -> dict:
        result: dict = {}
        result["update_channel"] = from_str(self.update_channel)
        result["debug_logging"] = from_bool(self.debug_logging)
        result["log_file_size_mb"] = from_int(self.log_file_size_mb)
        result["log_file_count"] = from_int(self.log_file_count)
        result["update_manifest_url"] = from_str(self.update_manifest_url)
        result["zabbix_proxy_container"] = to_class(ZabbixProxyContainer, self.zabbix_proxy_container)
        result["zabbix_mysql_container"] = from_union([lambda x: to_class(ZabbixMysqlContainer, x), from_none], self.zabbix_mysql_container)
        return result


    
