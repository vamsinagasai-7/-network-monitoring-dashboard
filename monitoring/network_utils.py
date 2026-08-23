import subprocess
import platform


def ping_device(ip_address):
    system = platform.system()

    if system == "Windows":
        command = ["ping", "-n", "1", ip_address]
    else:
        command = ["ping", "-c", "1", ip_address]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return result.returncode == 0