import subprocess
import shlex

def run_eth_wallet_command(args):
    """Run an eth-wallet CLI command and return the output as string."""
    cmd = f"eth-wallet {args}"
    try:
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return e.stderr or str(e)

# Get wallet info (address, pub key)
def get_wallet_info():
    return run_eth_wallet_command("get-wallet")

# Get ETH or token balance
def get_wallet_balance(token=None):
    if token:
        return run_eth_wallet_command(f"get-balance --token {token}")
    return run_eth_wallet_command("get-balance")

# Send ETH transaction (interactive, will prompt for input)
def send_eth_transaction():
    return run_eth_wallet_command("send-transaction")

def send_transaction(to_address, value, passphrase=None):
    """Send ETH to a specified address with a given value (in ETH), optionally with passphrase for non-interactive use."""
    if passphrase:
        # If CLI supports --password, use it; otherwise, simulate input
        cmd = f"send-transaction --to {to_address} --value {value}"
        process = subprocess.Popen(
            shlex.split(f"eth-wallet {cmd}"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            # Send passphrase to stdin when prompted
            stdout, stderr = process.communicate(input=passphrase + "\n", timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        if process.returncode == 0:
            return stdout
        else:
            return stderr or stdout or "Error sending transaction."
    else:
        return run_eth_wallet_command(f"send-transaction --to {to_address} --value {value}")

# Add new ERC20 token (interactive)
def add_token():
    return run_eth_wallet_command("add-token")

# List all added tokens
def list_tokens():
    return run_eth_wallet_command("list-tokens")

# Show connected network
def get_network():
    return run_eth_wallet_command("network")

# Reveal wallet master private key (interactive)
def reveal_seed():
    return run_eth_wallet_command("reveal-seed")

# Restore wallet (interactive)
def restore_wallet():
    return run_eth_wallet_command("restore-wallet")

print(get_wallet_balance())