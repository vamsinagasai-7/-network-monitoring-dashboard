import subprocess
import re
import socket
import ipaddress

from concurrent.futures import ThreadPoolExecutor

from flask import Flask, render_template

# Scapy is used only for ARP discovery
try:
    from scapy.all import ARP, Ether, srp
    from scapy.data import ManufDA

    SCAPY_AVAILABLE = True

except Exception as error:
    print("Scapy could not be loaded:", error)

    SCAPY_AVAILABLE = False


app = Flask(__name__)


# ========================================
# GET LOCAL IP
# ========================================

def get_local_ip():

    hostname = socket.gethostname()

    try:

        local_ip = socket.gethostbyname(hostname)

        return local_ip

    except socket.gaierror:

        # Fallback method

        result = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        try:

            result.connect(("8.8.8.8", 80))

            local_ip = result.getsockname()[0]

        finally:

            result.close()

        return local_ip


# ========================================
# GET LOCAL NETWORK
# ========================================

def get_local_network():

    local_ip = get_local_ip()

    network = ipaddress.ip_network(
        local_ip + "/24",
        strict=False
    )

    return network


# ========================================
# GET VENDOR FROM MAC
# ========================================

def get_vendor(mac):

    if mac == "Unknown":
        return "Unknown"

    if not SCAPY_AVAILABLE:
        return "Unknown"

    try:

        result = ManufDA.lookup(mac)

        if result:

            if isinstance(result, tuple):

                if len(result) > 1 and result[1]:

                    return result[1]

                if len(result) > 0 and result[0]:

                    return result[0]

            return str(result)

    except Exception:

        pass

    return "Unknown"


# ========================================
# ARP DISCOVERY
# ========================================

def arp_discovery(network):

    devices = {}

    print()
    print("Starting ARP discovery...")
    print("Network:", network)

    # If Scapy is unavailable,
    # simply return an empty result.
    #
    # Ping discovery will continue.

    if not SCAPY_AVAILABLE:

        print("Scapy unavailable.")
        print("Skipping ARP discovery.")

        return devices

    try:

        # Create ARP request

        arp_request = ARP(
            pdst=str(network)
        )

        # Ethernet broadcast

        ethernet_frame = Ether(
            dst="ff:ff:ff:ff:ff:ff"
        )

        # Combine Ethernet + ARP

        packet = ethernet_frame / arp_request

        # Send ARP request

        answered, unanswered = srp(
            packet,
            timeout=2,
            verbose=False
        )

        # Process replies

        for sent, received in answered:

            ip = received.psrc

            mac = received.hwsrc.upper()

            devices[ip] = {
                "ip": ip,
                "mac": mac
            }

        print(
            "ARP discovered:",
            len(devices),
            "devices"
        )

    except Exception as error:

        print()
        print("ARP discovery failed.")
        print("Reason:", error)
        print("Continuing with ping discovery...")

    return devices


# ========================================
# GET WINDOWS ARP TABLE
# ========================================

def get_arp_table():

    arp_table = {}

    try:

        result = subprocess.run(

            ["arp", "-a"],

            capture_output=True,

            text=True,

            timeout=5
        )

        for line in result.stdout.splitlines():

            # Windows example:
            #
            # 172.22.8.1
            # dc-68-0c-3a-e7-ab
            # dynamic

            match = re.search(

                r"(\d+\.\d+\.\d+\.\d+)\s+"
                r"([0-9a-fA-F-]{17})\s+"
                r"(dynamic|static)",

                line,

                re.IGNORECASE
            )

            if match:

                ip = match.group(1)

                mac = match.group(2)

                mac = mac.replace("-", ":")

                mac = mac.upper()

                arp_table[ip] = mac

    except Exception as error:

        print(
            "Could not read ARP table:",
            error
        )

    return arp_table


# ========================================
# PING ONE IP
# ========================================

def ping_device(ip):

    try:

        result = subprocess.run(

            [
                "ping",

                "-a",

                "-n",
                "1",

                "-w",
                "500",

                ip
            ],

            capture_output=True,

            text=True,

            timeout=2
        )

        output = result.stdout


        # ==================================
        # PING SUCCESS
        # ==================================

        if result.returncode == 0:

            # ------------------------------
            # HOSTNAME
            # ------------------------------

            hostname = "Unknown"

            hostname_match = re.search(

                r"Pinging\s+([^\s\[]+)",

                output,

                re.IGNORECASE
            )

            if hostname_match:

                hostname = hostname_match.group(1)

                # Don't use IP as hostname

                if hostname == ip:

                    hostname = "Unknown"


            # ------------------------------
            # LATENCY
            # ------------------------------

            latency_match = re.search(

                r"time[=<]\s*(\d+)\s*ms",

                output,

                re.IGNORECASE
            )

            if latency_match:

                latency = (
                    latency_match.group(1)
                    + " ms"
                )

            else:

                latency = "Less than 1 ms"


            return {
                "ip": ip,
                "name": hostname,
                "ping": True,
                "latency": latency
            }


        # ==================================
        # PING FAILED
        # ==================================

        return {
            "ip": ip,
            "name": "Unknown",
            "ping": False,
            "latency": "N/A"
        }


    except Exception:

        return {
            "ip": ip,
            "name": "Unknown",
            "ping": False,
            "latency": "N/A"
        }


# ========================================
# PING ENTIRE NETWORK
# ========================================

def ping_network(network):

    print()
    print("Starting ping discovery...")

    ip_list = [
        str(ip)
        for ip in network.hosts()
    ]

    print(
        "IPs to check:",
        len(ip_list)
    )

    results = []

    # Run many pings at the same time

    with ThreadPoolExecutor(
        max_workers=50
    ) as executor:

        results = list(
            executor.map(
                ping_device,
                ip_list
            )
        )

    ping_devices = {}

    for result in results:

        ping_devices[result["ip"]] = result

    online_count = sum(
        1
        for result in results
        if result["ping"]
    )

    print(
        "Ping replies:",
        online_count
    )

    return ping_devices


# ========================================
# MERGE ARP + PING
# ========================================

def merge_devices(
    arp_devices,
    ping_devices,
    arp_table
):

    all_ips = set()

    # Add IPs found by ARP

    all_ips.update(
        arp_devices.keys()
    )

    # Add IPs found by ping

    for ip, result in ping_devices.items():

        if result["ping"]:

            all_ips.add(ip)


    devices = []


    # Process every discovered IP

    for ip in sorted(
        all_ips,
        key=lambda address:
        tuple(
            int(part)
            for part in address.split(".")
        )
    ):

        # ------------------------------
        # ARP MAC
        # ------------------------------

        mac = "Unknown"


        if ip in arp_devices:

            mac = arp_devices[ip]["mac"]

        elif ip in arp_table:

            mac = arp_table[ip]


        # ------------------------------
        # PING INFORMATION
        # ------------------------------

        ping_info = ping_devices.get(ip)


        if ping_info and ping_info["ping"]:

            hostname = ping_info["name"]

            status = "Online"

            latency = ping_info["latency"]


        else:

            hostname = "Unknown"

            status = "ARP Detected"

            latency = "N/A"


        # ------------------------------
        # VENDOR
        # ------------------------------

        vendor = get_vendor(mac)


        # ------------------------------
        # CREATE DEVICE
        # ------------------------------

        devices.append({

            "name": hostname,

            "ip": ip,

            "mac": mac,

            "vendor": vendor,

            "status": status,

            "latency": latency
        })


    return devices


# ========================================
# MAIN DISCOVERY
# ========================================

def discover_devices():

    print()
    print("================================")
    print("       NETWORK DISCOVERY")
    print("================================")


    # ------------------------------------
    # LOCAL IP
    # ------------------------------------

    local_ip = get_local_ip()

    print(
        "Local IP:",
        local_ip
    )


    # ------------------------------------
    # NETWORK
    # ------------------------------------

    network = get_local_network()

    print(
        "Network:",
        network
    )


    # ------------------------------------
    # STEP 1
    # ARP DISCOVERY
    # ------------------------------------

    arp_devices = arp_discovery(
        network
    )


    # ------------------------------------
    # STEP 2
    # PING DISCOVERY
    # ------------------------------------

    ping_devices = ping_network(
        network
    )


    # ------------------------------------
    # STEP 3
    # READ ARP TABLE
    # ------------------------------------

    arp_table = get_arp_table()


    # ------------------------------------
    # STEP 4
    # MERGE EVERYTHING
    # ------------------------------------

    devices = merge_devices(

        arp_devices,

        ping_devices,

        arp_table
    )


    # ------------------------------------
    # STATISTICS
    # ------------------------------------

    online = 0

    arp_only = 0


    for device in devices:

        if device["status"] == "Online":

            online += 1

        else:

            arp_only += 1


    print()
    print("================================")
    print(
        "Total discovered:",
        len(devices)
    )
    print(
        "Ping online:",
        online
    )
    print(
        "ARP detected:",
        arp_only
    )
    print("================================")
    print()


    return devices


# ========================================
# FLASK HOME PAGE
# ========================================

@app.route("/")
def home():

    print("Loading dashboard...")


    devices = discover_devices()


    # ------------------------------------
    # SUMMARY
    # ------------------------------------

    total_devices = len(devices)

    online_devices = 0

    offline_devices = 0


    for device in devices:

        if device["status"] == "Online":

            online_devices += 1

        else:

            offline_devices += 1


    # ------------------------------------
    # SEND TO HTML
    # ------------------------------------

    return render_template(

        "index.html",

        devices=devices,

        total_devices=total_devices,

        online_devices=online_devices,

        offline_devices=offline_devices
    )


# ========================================
# START FLASK
# ========================================

if __name__ == "__main__":

    # IMPORTANT:
    # debug=False prevents Flask's
    # reloader from running the network
    # scan twice.

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=False
    )