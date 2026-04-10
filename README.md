# Wallet Auditing Framework

A comprehensive machine learning-powered system for assessing Ethereum wallet risk and security. This framework analyzes wallet behavior, transaction patterns, and associations to detect potentially fraudulent or high-risk addresses using an ensemble of specialized ML models.

## Project Overview

The Wallet Auditing Framework combines multiple analytical dimensions:

- **Behavioral Analysis**: Examines transaction patterns, frequency, and characteristics
- **Association Analysis**: Identifies relationships between wallets and known malicious entities
- **Contextual Analysis**: Considers broader network context and risk indicators
- **Ensemble Scoring**: Combines multiple ML models for robust risk assessment

The system provides a REST API backend and an interactive React dashboard for visualization and analysis.

## Architecture

```
wallet auditing framework/
├── eth-wallet/              # Flask API backend & core scoring engine
├── Model Training/          # ML model training & optimization notebooks
├── frontend/                # React-based dashboard
└── ethereum-api-quickstart/ # Blockchain API integration utilities
```

## Prerequisites

Before setting up the project, ensure you have:

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **API Keys** for:
  - [Etherscan](https://etherscan.io/apis) - Blockchain data
  - [Alchemy](https://www.alchemy.com/) - Ethereum RPC & data
  - [OpenAI](https://platform.openai.com/api-keys) - AI-powered analysis (optional)

## Installation & Setup

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd "wallet auditing framework"
```

### 2. Set Up Python Virtual Environment

Create and activate a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

### 3. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and populate the following variables:

```env
# Required API Keys
ETHERSCAN_API_KEY=your_etherscan_api_key
ALCHEMY_API_KEY=your_alchemy_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional, for advanced features

# Model & Data Configuration
MODEL_DIR=Model Training
BLACKLIST_PATH=blacklist_database.json

# API Configuration (adjust if needed)
ETHERSCAN_BASE_URL=https://api.etherscan.io/v2/api
ALCHEMY_BASE_URL=https://eth-mainnet.g.alchemy.com/v2
ETHERSCAN_DELAY=0.2
ALCHEMY_DELAY=0.1
```

### 4. Install Python Dependencies

Install required Python packages:

```bash
pip install -r eth-wallet/requirements.txt
```

Key dependencies include:
- **Flask**: REST API framework
- **scikit-learn, XGBoost, LightGBM**: Machine learning models
- **pandas, numpy**: Data processing
- **SHAP**: Model explainability
- **requests, python-dotenv**: Utilities
- **langchain**: LLM integration

## Data & Models

### Dataset

The framework uses ensemble ML models trained on blockchain transaction data. The primary dataset is located at:

```
Model Training/dataset_v2.csv
```

This dataset contains features for wallet behavior, transaction patterns, and classification labels.

### Pre-trained Models

The following pre-trained models are required for the API to function:

```
Model Training/
├── behavioral_xgboost_optimized.pkl
├── behavioral_scaler_optimized.pkl
├── association_gradientboosting_optimized.pkl
├── association_scaler_optimized.pkl
├── contextual_xgboost_optimized.pkl
├── contextual_scaler_optimized.pkl
└── ensemble_config_optimized.json
```

Plus the blacklist database:

```
blacklist_database.json
```

## Usage Guide

### Option A: Run the Full Application Stack

Open **three terminal windows** in the project root:

#### Terminal 1: Start the Backend API

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Navigate to backend
cd eth-wallet

# Start Flask server
flask run --app api_server.py
```

The API will be available at `http://127.0.0.1:5001`

#### Terminal 2: Start the React Frontend

```bash
# From project root
cd frontend/blockchain-security-framework

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The dashboard will be available at `http://localhost:5173` (or another port if 5173 is busy)

#### Terminal 3: Access the Application

Once both servers are running, navigate to `http://localhost:5173` in your browser to use the interactive wallet auditing dashboard.

### Option B: Use the API Directly

If you only need the backend API, follow Terminals 1 and use a tool like `curl`, Postman, or `requests` library to interact with endpoints.

## Model Development & Customization

### Fine-tune Model Parameters

If you want to optimize the ML model hyperparameters:

```bash
# From project root
cd "Model Training"
jupyter notebook model_optimization.ipynb
```

This notebook allows you to:
- Experiment with different algorithm parameters
- Evaluate model performance on validation data
- Tune ensemble weights
- Save optimized model configurations

### Retrain Models from Scratch

To retrain all ensemble models with your own data or updated configurations:

```bash
# From project root
cd "Model Training"
jupyter notebook wallet_risk_ensemble_v2.ipynb
```

This notebook includes:
- Feature engineering from raw blockchain data
- Splitting data into train/validation/test sets
- Training behavioral, association, and contextual models
- Creating ensemble predictions
- Evaluating model performance
- Saving trained models and scalers

After retraining, ensure the updated model files are copied to `eth-wallet/` if needed.

## API Endpoints

The Flask backend provides the following key endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wallet` | GET | Retrieve wallet information |
| `/api/balance` | GET | Get wallet balance (ETH) |
| `/api/score` | POST | Get risk score for a wallet address |
| `/api/tokens` | GET | List available ERC20 tokens |
| `/api/network` | GET | Get current network information |
| `/api/blacklist` | GET | Check if address is on blacklist |

## Frontend Dashboard

The React dashboard (`frontend/blockchain-security-framework/`) provides:

- **Wallet Search**: Look up any Ethereum address
- **Risk Scoring**: View ML-generated risk scores
- **Transaction History**: Browse wallet transaction data
- **Visualization**: Charts and graphs of wallet behavior
- **Blacklist Status**: Check against known malicious addresses

## Project Structure

```
├── eth-wallet/                          # Backend API & core engine
│   ├── api_server.py                    # Flask API server
│   ├── wallet_risk_assessment.py        # Scoring engine
│   ├── eth_wallet/                      # Core library
│   └── requirements.txt                 # Python dependencies
│
├── Model Training/                      # ML model development
│   ├── wallet_risk_ensemble_v2.ipynb    # Model training notebook
│   ├── model_optimization.ipynb         # Hyperparameter tuning
│   ├── dataset_v2.csv                   # Training dataset
│   └── *.pkl                            # Trained model artifacts
│
├── frontend/
│   └── blockchain-security-framework/   # React dashboard
│       ├── package.json
│       └── src/
│
├── .env.example                         # Environment variables template
├── blacklist_database.json              # Known malicious addresses
└── README.md                            # This file
```

## Troubleshooting

### Issue: Models not found when starting API

**Solution**: Ensure that the pre-trained model files (`.pkl` files) exist in the `Model Training/` directory. You may need to retrain models using the Jupyter notebooks.

### Issue: API Key errors from Etherscan/Alchemy

**Solution**: Double-check that your `.env` file contains valid API keys. Test them by visiting the service websites directly. Also verify rate limiting isn't blocking requests (adjust `ETHERSCAN_DELAY` and `ALCHEMY_DELAY` if needed).

### Issue: Frontend cannot connect to backend

**Solution**: Verify the Flask server is running on `http://127.0.0.1:5001` and check that CORS is enabled in `api_server.py`.

### Issue: Port already in use

**Solution**: 
- For Flask (5001): Use `flask run --port 5002` to use a different port
- For React (5173): Vite will automatically try the next available port

## Contributing

When contributing to this project:

1. Create a new branch for your feature/fix
2. Include tests and documentation
3. Ensure pre-trained models are not committed (they're too large)
4. Update `.env.example` if new environment variables are added

## License

See `LICENSE` file for details.

## Support

For issues, questions, or feedback, please open an issue on the project repository.

---

**Note**: This framework is designed for educational and research purposes. Always verify results independently and use proper security practices when working with blockchain data and wallets.
