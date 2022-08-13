from dataclasses import dataclass
from typing import Optional, Any, List, TypeVar, Type, cast, Callable

T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


@dataclass
class Config:
    dynamic: dict
    static: dict
    secrets: dict

    @staticmethod
    def from_dict(obj: Any) -> 'Config':
        assert isinstance(obj, dict)
        dynamic = obj.get("dynamic")
        static = obj.get("static")
        secrets = obj.get("secrets")
        return Config(dynamic, static, secrets)

    def to_dict(self) -> dict:
        result: dict = {}
        result["dynamic"] = self.dynamic
        result["static"] = self.static
        result["secrets"] = self.secrets
        return result


@dataclass
class MappedFile:
    name: str
    host_path: str
    host_path_dynamic: bool
    container_path: str

    @staticmethod
    def from_dict(obj: Any) -> 'MappedFile':
        assert isinstance(obj, dict)
        name = from_str(obj.get("name"))
        host_path = from_str(obj.get("host_path"))
        host_path_dynamic = from_bool(obj.get("host_path_dynamic"))
        container_path = from_str(obj.get("container_path"))
        return MappedFile(name, host_path, host_path_dynamic, container_path)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_str(self.name)
        result["host_path"] = from_str(self.host_path)
        result["host_path_dynamic"] = from_bool(self.host_path_dynamic)
        result["container_path"] = from_str(self.container_path)
        return result


@dataclass
class Port:
    host_port: int
    container_port: int
    protocol: str

    @staticmethod
    def from_dict(obj: Any) -> 'Port':
        assert isinstance(obj, dict)
        host_port = from_int(obj.get("host_port"))
        container_port = from_int(obj.get("container_port"))
        protocol = from_str(obj.get("protocol"))
        return Port(host_port, container_port, protocol)

    def to_dict(self) -> dict:
        result: dict = {}
        result["host_port"] = from_int(self.host_port)
        result["container_port"] = from_int(self.container_port)
        result["protocol"] = from_str(self.protocol)
        return result


@dataclass
class ContainerConfig:
    name: str
    hostname: str
    image: str
    privileged: bool
    config: Config
    files: Optional[List[MappedFile]] = None
    ports: Optional[List[Port]] = None

    @staticmethod
    def from_dict(obj: Any) -> 'ContainerConfig':
        assert isinstance(obj, dict)
        name = from_str(obj.get("name"))
        hostname = from_str(obj.get("hostname"))
        image = from_str(obj.get("image"))
        privileged = from_bool(obj.get("privileged"))
        config = Config.from_dict(obj.get("config"))
        files = from_union([lambda x: from_list(MappedFile.from_dict, x), from_none], obj.get("files"))
        ports = from_union([lambda x: from_list(Port.from_dict, x), from_none], obj.get("ports"))
        return ContainerConfig(name, hostname, image, privileged, config, files, ports)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_str(self.name)
        result["hostname"] = from_str(self.hostname)
        result["image"] = from_str(self.image)
        result["privileged"] = from_bool(self.privileged)
        result["config"] = to_class(Config, self.config)
        result["files"] = from_union([lambda x: from_list(lambda x: to_class(MappedFile, x), x), from_none], self.files)
        result["ports"] = from_union([lambda x: from_list(lambda x: to_class(Port, x), x), from_none], self.ports)
        return result


@dataclass
class UpdateManifest:
    package_version: str
    containers: List[ContainerConfig]
    dynamic_secrets: Optional[List[str]] = None

    @staticmethod
    def from_dict(obj: Any) -> 'UpdateManifest':
        assert isinstance(obj, dict)
        package_version = from_str(obj.get("package_version"))
        containers = from_list(ContainerConfig.from_dict, obj.get("containers"))
        dynamic_secrets = from_union([lambda x: from_list(from_str, x), from_none], obj.get("dynamic_secrets"))
        return UpdateManifest(package_version, containers, dynamic_secrets)

    def to_dict(self) -> dict:
        result: dict = {}
        result["package_version"] = from_str(self.package_version)
        result["containers"] = from_list(lambda x: to_class(ContainerConfig, x), self.containers)
        result["dynamic_secrets"] = from_union([lambda x: from_list(from_str, x), from_none], self.dynamic_secrets)
        return result
