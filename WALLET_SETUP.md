# Wallet Configuration on Render

## Overview
Your wallet credentials are securely managed through environment variables, not committed to git. The `.env` file is ignored by git for security.

## Setup Steps

### 1. Local Development
Your `.env` file already contains:
```
WALLET_ADDRESS=0x51F724786F1f59924215B41baDDe959825E28010
SECRET_KEY=0x45e826...
```

These are automatically loaded when you run:
- `./start-production.sh` (loads .env before starting Flask)
- Flask app calls `load_dotenv()` at startup

### 2. Render Deployment
To set wallet configuration on Render:

1. **Go to your Render Dashboard** → Select your service
2. **Navigate to Environment** (in the left sidebar)
3. **Add the following environment variables:**
   - `WALLET_ADDRESS`: `0x51F724786F1f59924215B41baDDe959825E28010`
   - `SECRET_KEY`: `0x45e826f831a34242c3145ce2dd99189efe77f0d1bd3bf45d298b29bf5767fd64873e5dabe1eec6a808c7faa031843625449c2c21e5fef0cb033f07934b211cb7`
   - (Optional) `INFURA_API_KEY` - if using Infura for Web3 provider
   - (Optional) `ETHERSCAN_API_KEY` - for address verification features

4. **Deploy** (re-deploy your service or wait for auto-deploy if connected to GitHub)

### 3. How It Works

The configuration system now prioritizes environment variables:

```python
# In eth-wallet/eth_wallet/configuration.py
def load_configuration(self):
    # Priority 1: Check environment variables
    env_wallet_address = os.getenv('WALLET_ADDRESS', '').strip()
    
    if env_wallet_address:
        # Use environment variables (works on Render)
        self.eth_address = env_wallet_address
        self.public_key = env_secret_key
    else:
        # Fallback to ~/.eth-wallet/config.yaml (doesn't persist on Render)
```

### 4. Security Notes
- ✅ `.env` file is in `.gitignore` - never committed to git
- ✅ Credentials stored as Render environment variables - encrypted at rest
- ✅ Environment variables are injected at runtime, not in source code
- ✅ Each environment can have different wallet addresses (local vs production)

### 5. Verification
Once deployed to Render, the `/api/wallet` endpoint should return:
```json
{
  "address": "0x51F724786F1f59924215B41baDDe959825E28010",
  "pub_key": "0x45e826f831..."
}
```

And `/api/balance` should return the Sepolia testnet balance.

### 6. Changing Wallet Address
To use a different wallet:
1. Update the environment variables on Render dashboard
2. Trigger a re-deploy
3. The Flask app will automatically load the new credentials

No code changes needed!
