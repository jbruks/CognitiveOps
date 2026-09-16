import ipaddress
import json
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


EXPECTED_BUFFERS = {
    "attT",
    "attW",
    "attX",
    "attY",
    "attZ",
}


def _get_local_networks():
    result = subprocess.run(
        ["ip", "-o", "-f", "inet", "addr", "show"],
        capture_output=True,
        text=True,
        check=True,
    )

    networks = []

    for line in result.stdout.splitlines():
        parts = line.split()

        if "inet" not in parts:
            continue

        interface = parts[1]
        cidr = parts[parts.index("inet") + 1]

        if (
            interface == "lo"
            or interface.startswith("docker")
            or interface.startswith("br-")
            or interface.startswith("veth")
        ):
            continue

        ip_interface = ipaddress.ip_interface(cidr)

        networks.append(
            (
                interface,
                ip_interface.ip,
                ip_interface.network,
            )
        )

    return networks


def _check_phyphox_host(ip, timeout_s=0.4):
    url = f"http://{ip}/config"

    try:
        with urllib.request.urlopen(
            url,
            timeout=timeout_s,
        ) as response:
            data = json.load(response)

        if data.get("title") not in ("Actitud", "ActitudPosicion"):
            return None

        buffers = {
            item.get("name")
            for item in data.get("buffers", [])
            if item.get("name")
        }

        if not EXPECTED_BUFFERS.issubset(buffers):
            return None

        return f"http://{ip}"

    except Exception:
        return None


def discover_phyphox_attitude(
    timeout_s=0.4,
    max_workers=32,
):
    networks = _get_local_networks()

    candidate_ips = []

    for _, own_ip, network in networks:
        for ip in network.hosts():
            if ip != own_ip:
                candidate_ips.append(ip)

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        futures = [
            executor.submit(
                _check_phyphox_host,
                ip,
                timeout_s,
            )
            for ip in candidate_ips
        ]

        for future in as_completed(futures):
            result = future.result()

            if result is not None:
                return result

    return None


if __name__ == "__main__":
    endpoint = discover_phyphox_attitude()

    if endpoint is None:
        print("phyphox Actitud not found")
    else:
        print(f"phyphox Actitud found at {endpoint}")
