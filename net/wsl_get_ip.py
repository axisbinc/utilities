import subprocess

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

# Example usage
if __name__ == "__main__":
    wsl_ip_cidr = get_wsl_ip_cidr()
    if wsl_ip_cidr:
        print(f"WSL IP Address in CIDR notation: {wsl_ip_cidr}")
    else:
        print("Could not determine the WSL IP address.")
