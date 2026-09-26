import platform
import shutil


def os_name() -> str:
    return platform.system()


def is_linux() -> bool:
    return os_name() == "Linux"


def is_windows() -> bool:
    return os_name() == "Windows"


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def has_ollama() -> bool:
    return has_command("ollama")


def has_docker() -> bool:
    return has_command("docker")
