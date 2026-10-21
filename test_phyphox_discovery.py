import ipaddress
import json
import socket
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


def get_local_networks():
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

        cidr = parts[parts.index("inet") + 1]

        interface = parts[1]

        if (interface == "lo"
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


def check_phyphox_host(ip, timeout=0.4):
    url = f"http://{ip}/config"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.load(response)

        title = data.get("title")

        buffers = {
            item.get("name")
            for item in data.get("buffers", [])
            if item.get("name")
        }

        if title != "ActitudPosicion":
            return None

        if not EXPECTED_BUFFERS.issubset(buffers):
            return None

        return {
            "ip": str(ip),
            "url": f"http://{ip}",
            "title": title,
        }

    except Exception:
        return None


def discover_phyphox():
    networks = get_local_networks()

    if not networks:
        print("No IPv4 networks found.")
        return None

    print("Local networks:")

    candidate_ips = []

    for interface, own_ip, network in networks:
        print(
            f"  {interface}: "
            f"{own_ip} on {network}"
        )

        for ip in network.hosts():
            if ip == own_ip:
                continue

            candidate_ips.append(ip)

    print()
    print(
        f"Scanning {len(candidate_ips)} hosts "
        f"for phyphox / Actitud..."
    )

    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = {
            executor.submit(check_phyphox_host, ip): ip
            for ip in candidate_ips
        }

        for future in as_completed(futures):
            result = future.result()

            if result is not None:
                return result

    return None


if __name__ == "__main__":
    result = discover_phyphox()

    print()

    if result is None:
        print("phyphox Actitud not found.")
    else:
        print("FOUND:")
        print(f"  title: {result['title']}")
        print(f"  ip:    {result['ip']}")
        print(f"  url:   {result['url']}")
