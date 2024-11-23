import subprocess
import argparse
import ipaddress
import sys

def get_wsl_ip_cidr():
    """Get the WSL eth0 IP address in CIDR notation."""
    try:
        # Run the `ip` command inside WSL to get eth0 details
        result = subprocess.run(
            ["wsl", "ip", "-4", "addr", "show", "eth0"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error running command: {result.stderr}")
            return None

        # Parse the output to extract the IP address and CIDR
        for line in result.stdout.splitlines():
            if "inet" in line:
                # Extract CIDR (e.g., "172.16.0.1/12")
                cidr = line.strip().split()[1]
                return cidr

        print("No IP address found for eth0.")
        return None
    except Exception as e:
        print(f"Error retrieving WSL IP address in CIDR format: {e}")
        return None

def get_network_adapters():
    """
    List all network adapters with their alias, index, IPv4 address, and default gateway.
    """
    cmd = [
        "powershell",
        "-Command",
        "Get-NetIPConfiguration | Select-Object InterfaceAlias, InterfaceIndex, IPv4Address, @{Name='IPv4DefaultGateway'; Expression={$_.IPv4DefaultGateway.NextHop}}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("Available Network Interfaces:")
        print(result.stdout)
    else:
        print(f"Failed to retrieve network adapters:\n{result.stderr}")

def get_gateway_from_nic(interface_index):
    """
    Retrieve the default gateway for the given NIC using its InterfaceIndex.
    """
    cmd = [
        "powershell",
        "-Command",
        f"Get-NetIPConfiguration | Where-Object {{ $_.InterfaceIndex -eq {interface_index} }} | Select-Object -ExpandProperty IPv4DefaultGateway | Select-Object -ExpandProperty NextHop"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        gateway = result.stdout.strip()
        if gateway:
            return gateway
        else:
            print(f"No gateway found for interface index '{interface_index}'.")
            return None
    else:
        print(f"Failed to retrieve gateway for interface index '{interface_index}':\n{result.stderr}")
        return None

def check_route_status(subnet):
    """Check if a route for the specified subnet exists."""
    cmd = ["route", "print"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to retrieve route information.")
        return False

    for line in result.stdout.splitlines():
        if subnet in line:
            print(f"Route exists for {subnet}:")
            print(line.strip())
            return True
    print(f"No route found for {subnet}.")
    return False

def delete_existing_route(subnet, dry_run):
    """Delete any existing route for the specified subnet."""
    cmd = ["route", "delete", subnet]
    if dry_run:
        print(f"[Dry Run] Command to delete route: {' '.join(cmd)}")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Deleted existing route for {subnet}:\n{result.stdout}")
        else:
            print(f"No existing route found for {subnet} or failed to delete:\n{result.stderr}")

def add_static_route(subnet, mask, gateway, interface_index, dry_run):
    """Add a static route for WSL traffic to a specific NIC."""
    cmd = [
        "route",
        "add",
        subnet,
        "MASK",
        mask,
        gateway,
        "IF",
        str(interface_index)
    ]
    if dry_run:
        print(f"[Dry Run] Command to add route: {' '.join(cmd)}")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Static route added successfully:\n{result.stdout}")
        else:
            print(f"Failed to add static route:\n{result.stderr}")

def parse_cidr(cidr):
    """Convert CIDR notation to subnet and mask."""
    try:
        network = ipaddress.IPv4Network(cidr, strict=False)
        subnet = str(network.network_address)
        mask = str(network.netmask)
        return subnet, mask
    except ValueError as e:
        print(f"Invalid CIDR format: {cidr}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Configure WSL network to use a specific NIC.")
    parser.add_argument("--cidr", help="WSL instance IP address in CIDR format (e.g., 172.16.0.0/12)")
    parser.add_argument("--gateway", help="Gateway IP address of the desired NIC")
    parser.add_argument("--interface-index", type=int, help="InterfaceIndex of the desired NIC")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode (print commands without executing)")
    parser.add_argument("--status", action="store_true", help="Check if the route to the WSL subnet exists")
    args = parser.parse_args()

    try:
        # Parse CIDR if provided or prompt for it
        if not args.cidr:
            args.cidr = get_wsl_ip_cidr()
            if not args.cidr:
                args.cidr = input("Enter the WSL instance IP address in CIDR format (e.g., 172.16.0.0/12): ")

        # Parse CIDR to get subnet and mask
        subnet, mask = parse_cidr(args.cidr)

        # Handle --status option
        if args.status:
            check_route_status(subnet)
            return

        # If interface index is missing, prompt the user
        if not args.interface_index:
            print("Available network adapters:")
            get_network_adapters()
            args.interface_index = int(input("Enter the InterfaceIndex of the desired NIC: "))

        # Derive the gateway if not provided
        if not args.gateway:
            args.gateway = get_gateway_from_nic(args.interface_index)
            if not args.gateway:
                print("Unable to determine the gateway. Please provide it manually.")
                args.gateway = input("Enter the gateway IP address of the desired NIC: ")

        # Delete any existing route for the subnet
        delete_existing_route(subnet, args.dry_run)

        # Add the static route
        add_static_route(subnet, mask, args.gateway, args.interface_index, args.dry_run)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
