"""
Wallet Risk Scoring - Inference Script
======================================
This script scores a single wallet address using the trained ensemble model.

Usage:
    python wallet_scoring.py <wallet_address>
    
Example:
    python wallet_scoring.py 0x1234567890abcdef1234567890abcdef12345678

The script will:
1. Fetch transaction history from Etherscan API
2. Fetch asset transfers from Alchemy API
3. Calculate all behavioral, association, and contextual features
4. Load the trained models and scalers
5. Generate risk score and prediction with SHAP explanations
"""

import sys
import os
import pandas as pd
import numpy as np
import requests
import json
import time
import joblib
import shap
from datetime import datetime
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETHERSCAN_BASE_URL = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api")

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
ALCHEMY_BASE_URL = f"{os.getenv('ALCHEMY_BASE_URL')}/{ALCHEMY_API_KEY}"

# Model paths
MODEL_DIR = os.getenv("MODEL_DIR", "Model Training")
BEHAVIORAL_MODEL_PATH = f"{MODEL_DIR}/behavioral_xgboost_optimized.pkl"
BEHAVIORAL_SCALER_PATH = f"{MODEL_DIR}/behavioral_scaler_optimized.pkl"
ASSOCIATION_MODEL_PATH = f"{MODEL_DIR}/association_gradientboosting_optimized.pkl"
ASSOCIATION_SCALER_PATH = f"{MODEL_DIR}/association_scaler_optimized.pkl"
CONTEXTUAL_MODEL_PATH = f"{MODEL_DIR}/contextual_xgboost_optimized.pkl"
CONTEXTUAL_SCALER_PATH = f"{MODEL_DIR}/contextual_scaler_optimized.pkl"
ENSEMBLE_CONFIG_PATH = f"{MODEL_DIR}/ensemble_config_v1.json"
UNIFIED_BLACKLIST_PATH = os.getenv("BLACKLIST_PATH", "blacklist_database.json")

# Rate limiting
ETHERSCAN_DELAY = float(os.getenv("ETHERSCAN_DELAY", "0.2"))  # 5 calls per second
ALCHEMY_DELAY = float(os.getenv("ALCHEMY_DELAY", "0.1"))    # 10 calls per second

# Feature definitions
BEHAVIORAL_FEATURES = [
    'Avg min between sent tnx',
    'Avg min between received tnx',
    'Time Diff between first and last (Mins)',
    'Sent tnx',
    'Received Tnx',
    'Number of Created Contracts',
    'total transactions (including tnx to create contract)',
    'total Ether sent',
    'total ether received'
]

ASSOCIATION_FEATURES = [
    'No. of txns from blacklisted addresses',
    'No. of txns to blacklisted addresses',
    'Total ether sent to blacklisted addresses',
    'Ratio of total sent to blacklisted addresses',
    'Total ether received from blacklisted addresses',
    'Ratio of total received from blacklisted addresses',
    'unique_wallets_interacted_with',
    'num_blacklisted_contracts_interacted',
    'ratio_blacklisted_contract_txns'
]

CONTEXTUAL_FEATURES = [
    'avg_gas_price_gwei',
    'gas_price_std_dev',
    'high_gas_price_ratio',
    'low_gas_price_ratio',
    'gas_price_coefficient_variation',
    'total_failed_txns',
    'failed_txn_ratio',
    'max_consecutive_failures',
    'failed_contract_interaction_ratio',
    'total_erc721_transfers',
    'erc721_incoming_ratio',
    'erc721_outgoing_ratio',
    'unique_erc721_tokens',
    'external_txn_ratio',
    'erc20_txn_ratio',
    'erc721_txn_ratio',
    'erc1155_txn_ratio',
    'internal_txn_ratio'
]

# ============================================================================
# API FUNCTIONS
# ============================================================================

def fetch_wallet_transactions(address):
    """Fetch transaction history from Etherscan API"""
    print(f"  → Fetching transactions from Etherscan...")
    try:
        params = {
            'chainid': 1,
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'asc',
            'apikey': ETHERSCAN_API_KEY
        }
        response = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=30)
        time.sleep(ETHERSCAN_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and 'result' in data:
                txns = pd.DataFrame(data['result'])
                print(f"Fetched {len(txns)} transactions")
                return txns
        print(f"No transactions found")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return pd.DataFrame()


def fetch_alchemy_transactions(address, direction='from'):
    """Fetch asset transfers from Alchemy API"""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "fromBlock": "0x0",
                "toBlock": "latest",
                "category": ["external", "erc20", "erc721", "erc1155", "internal"],
                "withMetadata": True,
                "excludeZeroValue": False,
                "maxCount": "0x3e8"  # 1000 transfers
            }]
        }
        
        if direction == 'from':
            payload["params"][0]["fromAddress"] = address
        else:
            payload["params"][0]["toAddress"] = address
        
        response = requests.post(ALCHEMY_BASE_URL, json=payload, timeout=30)
        time.sleep(ALCHEMY_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'transfers' in data['result']:
                return data['result']['transfers']
        return []
    except Exception as e:
        print(f"Error fetching Alchemy data: {e}")
        return []


# ============================================================================
# FEATURE CALCULATION FUNCTIONS
# ============================================================================

def calculate_behavioral_features(address, transactions_df):
    """Calculate behavioral features from transaction data"""
    print(f"  → Calculating behavioral features...")
    
    if transactions_df.empty:
        print(f"No transactions - using zero values")
        return [0] * 9
    
    address_lower = address.lower()
    
    # Sent and received transactions
    sent_txns = transactions_df[transactions_df['from'].str.lower() == address_lower]
    received_txns = transactions_df[transactions_df['to'].str.lower() == address_lower]
    
    # Time calculations
    timestamps = transactions_df['timeStamp'].astype(int).tolist()
    if len(timestamps) >= 2:
        timestamps_sorted = sorted(timestamps)
        time_diff_mins = (timestamps_sorted[-1] - timestamps_sorted[0]) / 60
        
        # Avg time between sent transactions
        if len(sent_txns) > 1:
            sent_times = sorted(sent_txns['timeStamp'].astype(int).tolist())
            avg_min_sent = sum([sent_times[i+1] - sent_times[i] for i in range(len(sent_times)-1)]) / (len(sent_times)-1) / 60
        else:
            avg_min_sent = 0
        
        # Avg time between received transactions
        if len(received_txns) > 1:
            received_times = sorted(received_txns['timeStamp'].astype(int).tolist())
            avg_min_received = sum([received_times[i+1] - received_times[i] for i in range(len(received_times)-1)]) / (len(received_times)-1) / 60
        else:
            avg_min_received = 0
    else:
        time_diff_mins = 0
        avg_min_sent = 0
        avg_min_received = 0
    
    # Contract creation (transactions with empty 'to' field)
    created_contracts = len(transactions_df[transactions_df['to'] == ''])
    
    # Ether calculations
    total_sent = sent_txns['value'].astype(float).sum() / 1e18
    total_received = received_txns['value'].astype(float).sum() / 1e18
    
    features = [
        avg_min_sent,
        avg_min_received,
        time_diff_mins,
        len(sent_txns),
        len(received_txns),
        created_contracts,
        len(transactions_df),
        total_sent,
        total_received
    ]
    
    print(f"Behavioral features calculated")
    return features


def calculate_association_features(address, transactions_df, blacklist_set):
    """Calculate association features using unified blacklist (9 features)"""
    print(f"  → Calculating association features...")
    
    if transactions_df.empty:
        print(f"No transactions - using zero values")
        return [0] * 9
    
    address_lower = address.lower()
    
    # Transactions FROM blacklisted addresses (received by this address)
    from_blacklisted = transactions_df[
        (transactions_df['to'].str.lower() == address_lower) &
        (transactions_df['from'].str.lower().isin(blacklist_set))
    ]
    
    # Transactions TO blacklisted addresses (sent by this address)
    to_blacklisted = transactions_df[
        (transactions_df['from'].str.lower() == address_lower) &
        (transactions_df['to'].str.lower().isin(blacklist_set))
    ]
    
    # Calculate totals
    total_sent = transactions_df[
        transactions_df['from'].str.lower() == address_lower
    ]['value'].astype(float).sum() / 1e18
    
    total_received = transactions_df[
        transactions_df['to'].str.lower() == address_lower
    ]['value'].astype(float).sum() / 1e18
    
    total_sent_to_blacklisted = to_blacklisted['value'].astype(float).sum() / 1e18
    total_received_from_blacklisted = from_blacklisted['value'].astype(float).sum() / 1e18
    
    # NEW FEATURES: Unique wallets and contracts interacted with
    to_addresses = set(transactions_df['to'].str.lower().dropna())
    from_addresses = set(transactions_df['from'].str.lower().dropna())
    all_counterparties = (to_addresses | from_addresses) - {address_lower}
    unique_wallets = len(all_counterparties)
    
    # Unique contracts interacted with
    if 'contractAddress' in transactions_df.columns:
        contract_addresses = transactions_df['contractAddress'].str.lower().dropna()
        contract_addresses = contract_addresses[contract_addresses != '']
        unique_contracts = contract_addresses.nunique()
    else:
        unique_contracts = 0
    
    # Number of blacklisted contract interactions
    num_blacklisted_contract_txns = 0
    if 'contractAddress' in transactions_df.columns:
        for _, row in transactions_df.iterrows():
            contract_addr = str(row.get('contractAddress', '')).lower()
            if contract_addr and contract_addr != '' and contract_addr in blacklist_set:
                num_blacklisted_contract_txns += 1
    
    # Ratio of blacklisted contract transactions
    total_txns = len(transactions_df)
    ratio_blacklisted_contract = num_blacklisted_contract_txns / total_txns if total_txns > 0 else 0.0
    
    features = [
        len(from_blacklisted),
        len(to_blacklisted),
        total_sent_to_blacklisted,
        total_sent_to_blacklisted / total_sent if total_sent > 0 else 0.0,
        total_received_from_blacklisted,
        total_received_from_blacklisted / total_received if total_received > 0 else 0.0,
        unique_wallets,
        num_blacklisted_contract_txns,
        ratio_blacklisted_contract
    ]
    
    print(f"Association features calculated")
    print(f"Transactions from blacklisted: {len(from_blacklisted)}")
    print(f"Transactions to blacklisted: {len(to_blacklisted)}")
    print(f"Unique wallets: {unique_wallets}, Unique contracts: {unique_contracts}")
    print(f"Blacklisted contract interactions: {num_blacklisted_contract_txns}")
    return features


def calculate_contextual_features(address, transactions_df):
    """
    Calculate contextual features (18 features from Etherscan + Alchemy data)
    Includes gas price patterns, error analysis, and NFT/transaction categorization.
    """
    print(f"Calculating contextual features...")
    
    if transactions_df.empty:
        print(f"No transactions - using zero values")
        return [0] * 18
    
    try:
        address_lower = address.lower()
        
        # Filter outgoing transactions for gas and error analysis
        outgoing_txns = transactions_df[transactions_df['from'].str.lower() == address_lower]
        
        # ===== GAS PRICE FEATURES (5 features) =====
        if not outgoing_txns.empty:
            gas_prices = outgoing_txns['gasPrice'].astype(float) / 1e9  # Convert to Gwei
            avg_gas_price = gas_prices.mean()
            gas_price_std = gas_prices.std()
            coef_variation = (gas_price_std / avg_gas_price) if avg_gas_price > 0 else 0.0
            
            # High gas price ratio (above 100 Gwei - urgency indicator)
            high_gas_count = (gas_prices > 100).sum()
            high_gas_ratio = high_gas_count / len(gas_prices) if len(gas_prices) > 0 else 0.0
            
            # Low gas price ratio (below 10 Gwei - hiding in low-traffic)
            low_gas_count = (gas_prices < 10).sum()
            low_gas_ratio = low_gas_count / len(gas_prices) if len(gas_prices) > 0 else 0.0
        else:
            avg_gas_price = gas_price_std = coef_variation = high_gas_ratio = low_gas_ratio = 0.0
        
        # ===== ERROR STATUS FEATURES (4 features) =====
        if not outgoing_txns.empty:
            failed_txns = outgoing_txns[outgoing_txns['isError'] == '1']
            total_failed = len(failed_txns)
            failed_ratio = total_failed / len(outgoing_txns)
            
            # Max consecutive failures
            consecutive_failures = 0
            max_consecutive_failures = 0
            for _, row in outgoing_txns.iterrows():
                if row['isError'] == '1':
                    consecutive_failures += 1
                    max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
                else:
                    consecutive_failures = 0
            
            # Failed contract interactions (transactions with input data)
            contract_txns = outgoing_txns[outgoing_txns['input'] != '0x']
            if not contract_txns.empty:
                failed_contract_txns = contract_txns[contract_txns['isError'] == '1']
                failed_contract_ratio = len(failed_contract_txns) / len(contract_txns)
            else:
                failed_contract_ratio = 0.0
        else:
            total_failed = failed_ratio = max_consecutive_failures = failed_contract_ratio = 0.0
        
        # ===== NFT AND TRANSACTION CATEGORY FEATURES (9 features) =====
        # Note: These require Alchemy API data. For now, set to 0 until Alchemy integration
        # TODO: Integrate fetch_all_alchemy_transactions() from contextual_features.py
        total_erc721 = erc721_incoming_ratio = erc721_outgoing_ratio = unique_erc721 = 0.0
        external_ratio = erc20_ratio = erc721_ratio = erc1155_ratio = internal_ratio = 0.0
        
        # Return features in correct order matching CONTEXTUAL_FEATURES
        features = [
            avg_gas_price,                  # avg_gas_price_gwei
            gas_price_std,                  # gas_price_std_dev
            high_gas_ratio,                 # high_gas_price_ratio
            low_gas_ratio,                  # low_gas_price_ratio
            coef_variation,                 # gas_price_coefficient_variation
            failed_ratio,                   # failed_txn_ratio
            max_consecutive_failures,       # max_consecutive_failures
            total_erc721,                   # total_erc721_transfers
            erc721_incoming_ratio,          # erc721_incoming_ratio
            erc721_outgoing_ratio,          # erc721_outgoing_ratio
            unique_erc721,                  # unique_erc721_tokens
            external_ratio,                 # external_txn_ratio
            erc20_ratio,                    # erc20_txn_ratio
            erc721_ratio,                   # erc721_txn_ratio
            erc1155_ratio,                  # erc1155_txn_ratio
            internal_ratio,                 # internal_txn_ratio
            total_failed,                   # total_failed_txns
            failed_contract_ratio           # failed_contract_interaction_ratio
        ]
        
        print(f"Contextual features calculated")
        print(f"      - Avg gas price: {avg_gas_price:.2f} Gwei, Std dev: {gas_price_std:.2f}")
        print(f"      - High gas ratio: {high_gas_ratio:.2%}, Low gas ratio: {low_gas_ratio:.2%}")
        print(f"      - Failed txns: {total_failed} ({failed_ratio:.2%}), Max consecutive: {max_consecutive_failures}")
        print(f"      - Failed contract ratio: {failed_contract_ratio:.2%}")
        return features
        
    except Exception as e:
        print(f"Error calculating contextual features: {e}")
        return [0] * 18


# ============================================================================
# MODEL LOADING AND INFERENCE
# ============================================================================

def load_models():
    """Load trained models, scalers, and configuration"""
    print("\n[Loading Models]")
    try:
        behavioral_model = joblib.load(BEHAVIORAL_MODEL_PATH)
        behavioral_scaler = joblib.load(BEHAVIORAL_SCALER_PATH)
        print(f"  ✓ Behavioral model loaded")
        
        association_model = joblib.load(ASSOCIATION_MODEL_PATH)
        association_scaler = joblib.load(ASSOCIATION_SCALER_PATH)
        print(f"  ✓ Association model loaded")
        
        contextual_model = joblib.load(CONTEXTUAL_MODEL_PATH)
        contextual_scaler = joblib.load(CONTEXTUAL_SCALER_PATH)
        print(f"  ✓ Contextual model loaded")
        
        with open(ENSEMBLE_CONFIG_PATH, 'r') as f:
            ensemble_config = json.load(f)
        print(f"  ✓ Ensemble configuration loaded")
        
        # Create SHAP explainers
        print(f"  ✓ Creating SHAP explainers...")
        explainer_behavioral = shap.TreeExplainer(behavioral_model)
        explainer_association = shap.TreeExplainer(association_model)
        explainer_contextual = shap.TreeExplainer(contextual_model)
        print(f"  ✓ SHAP explainers ready")
        
        return {
            'behavioral_model': behavioral_model,
            'behavioral_scaler': behavioral_scaler,
            'association_model': association_model,
            'association_scaler': association_scaler,
            'contextual_model': contextual_model,
            'contextual_scaler': contextual_scaler,
            'ensemble_config': ensemble_config,
            'explainer_behavioral': explainer_behavioral,
            'explainer_association': explainer_association,
            'explainer_contextual': explainer_contextual
        }
    except Exception as e:
        print(f"  ✗ Error loading models: {e}")
        sys.exit(1)


def load_blacklist():
    """Load unified blacklist"""
    print("\n[Loading Blacklist]")
    try:
        with open(UNIFIED_BLACKLIST_PATH, 'r') as f:
            unified_blacklist = json.load(f)
        blacklist_set = set(addr.lower() for addr in unified_blacklist)
        print(f"  ✓ Loaded {len(blacklist_set):,} blacklisted addresses")
        return blacklist_set
    except Exception as e:
        print(f"  ✗ Error loading blacklist: {e}")
        sys.exit(1)


# ============================================================================
# SHAP EXPLANATIONS
# ============================================================================

def calculate_shap_explanations(models, beh_scaled, ass_scaled, ctx_scaled, 
                                behavioral_features, association_features, contextual_features,
                                weights):
    """Calculate SHAP values for each dimension"""
    
    # Contribution threshold - only compute SHAP for significant dimensions
    CONTRIBUTION_THRESHOLD = 0.15
    
    explanations = {
        'behavioral': {'top_features': []},
        'association': {'top_features': []},
        'contextual': {'top_features': []}
    }
    
    # Behavioral dimension SHAP
    beh_contribution = weights['behavioral'] * models['behavioral_model'].predict_proba(beh_scaled)[0, 1]
    if beh_contribution >= CONTRIBUTION_THRESHOLD:
        print(f"  → Computing SHAP for Behavioral dimension (contribution: {beh_contribution:.4f})")
        shap_values_beh = models['explainer_behavioral'].shap_values(beh_scaled)
        # RandomForest returns (1, n_features, 2) - extract class 1 and flatten
        if shap_values_beh.ndim == 3:
            shap_values_beh = shap_values_beh[:, :, 1][0]  # Get fraud class, then first instance
        elif isinstance(shap_values_beh, list):
            shap_values_beh = shap_values_beh[1]
            if shap_values_beh.ndim == 2:
                shap_values_beh = shap_values_beh[0]
        elif shap_values_beh.ndim == 2:
            shap_values_beh = shap_values_beh[0]
        
        # Get top 5 features
        shap_abs = np.abs(shap_values_beh)
        top_indices = np.argsort(shap_abs)[-5:][::-1]
        
        for idx in top_indices:
            explanations['behavioral']['top_features'].append({
                'feature': BEHAVIORAL_FEATURES[idx],
                'shap_value': float(shap_values_beh[idx]),
                'impact': 'increases risk' if shap_values_beh[idx] > 0 else 'decreases risk',
                'feature_value': behavioral_features[idx]
            })
    
    # Association dimension SHAP
    ass_contribution = weights['association'] * models['association_model'].predict_proba(ass_scaled)[0, 1]
    if ass_contribution >= CONTRIBUTION_THRESHOLD:
        print(f"  → Computing SHAP for Association dimension (contribution: {ass_contribution:.4f})")
        shap_values_ass = models['explainer_association'].shap_values(ass_scaled)
        # RandomForest returns (1, n_features, 2) - extract class 1 and flatten
        if shap_values_ass.ndim == 3:
            shap_values_ass = shap_values_ass[:, :, 1][0]  # Get fraud class, then first instance
        elif isinstance(shap_values_ass, list):
            shap_values_ass = shap_values_ass[1]
            if shap_values_ass.ndim == 2:
                shap_values_ass = shap_values_ass[0]
        elif shap_values_ass.ndim == 2:
            shap_values_ass = shap_values_ass[0]
        
        # Get top 5 features
        shap_abs = np.abs(shap_values_ass)
        top_indices = np.argsort(shap_abs)[-5:][::-1]
        
        for idx in top_indices:
            explanations['association']['top_features'].append({
                'feature': ASSOCIATION_FEATURES[idx],
                'shap_value': float(shap_values_ass[idx]),
                'impact': 'increases risk' if shap_values_ass[idx] > 0 else 'decreases risk',
                'feature_value': association_features[idx]
            })
    
    # Contextual dimension SHAP
    ctx_contribution = weights['contextual'] * models['contextual_model'].predict_proba(ctx_scaled)[0, 1]
    if ctx_contribution >= CONTRIBUTION_THRESHOLD:
        print(f"  → Computing SHAP for Contextual dimension (contribution: {ctx_contribution:.4f})")
        shap_values_ctx = models['explainer_contextual'].shap_values(ctx_scaled)
        # RandomForest returns (1, n_features, 2) - extract class 1 and flatten
        if shap_values_ctx.ndim == 3:
            shap_values_ctx = shap_values_ctx[:, :, 1][0]  # Get fraud class, then first instance
        elif isinstance(shap_values_ctx, list):
            shap_values_ctx = shap_values_ctx[1]
            if shap_values_ctx.ndim == 2:
                shap_values_ctx = shap_values_ctx[0]
        elif shap_values_ctx.ndim == 2:
            shap_values_ctx = shap_values_ctx[0]
        
        # Get top 5 features
        shap_abs = np.abs(shap_values_ctx)
        top_indices = np.argsort(shap_abs)[-5:][::-1]
        
        for idx in top_indices:
            explanations['contextual']['top_features'].append({
                'feature': CONTEXTUAL_FEATURES[idx],
                'shap_value': float(shap_values_ctx[idx]),
                'impact': 'increases risk' if shap_values_ctx[idx] > 0 else 'decreases risk',
                'feature_value': contextual_features[idx]
            })
    
    print(f"  ✓ SHAP explanations generated")
    return explanations


def score_wallet(address, models, blacklist_set):
    """Score a wallet address and return risk assessment"""
    print(f"\n{'='*80}")
    print(f"SCORING WALLET: {address}")
    print(f"{'='*80}")
    
    # Fetch transaction data
    print("\n[Step 1/4] Fetching Transaction Data")
    transactions_df = fetch_wallet_transactions(address)
    
    # Calculate features
    print("\n[Step 2/4] Calculating Features")
    behavioral_features = calculate_behavioral_features(address, transactions_df)
    association_features = calculate_association_features(address, transactions_df, blacklist_set)
    contextual_features = calculate_contextual_features(address, transactions_df)
    
    # Scale features
    print("\n[Step 3/4] Scaling Features")
    beh_scaled = models['behavioral_scaler'].transform([behavioral_features])
    ass_scaled = models['association_scaler'].transform([association_features])
    ctx_scaled = models['contextual_scaler'].transform([contextual_features])
    print(f"  ✓ Features scaled")
    
    # Get dimension scores
    print("\n[Step 4/4] Generating Risk Assessment")
    beh_score = models['behavioral_model'].predict_proba(beh_scaled)[0, 1]
    ass_score = models['association_model'].predict_proba(ass_scaled)[0, 1]
    ctx_score = models['contextual_model'].predict_proba(ctx_scaled)[0, 1]
    
    # Get weights from config
    weights = models['ensemble_config']['weights']
    threshold = models['ensemble_config']['threshold']
    
    # Calculate weighted ensemble score
    final_score = (
        weights['behavioral'] * beh_score +
        weights['association'] * ass_score +
        weights['contextual'] * ctx_score
    )
    
    # Make prediction
    prediction = 'HIGH RISK' if final_score >= threshold else 'LOW RISK'
    
    print(f"  ✓ Risk assessment complete")
    
    # Calculate SHAP explanations
    print("\n[Step 5/5] Generating SHAP Explanations")
    shap_explanations = calculate_shap_explanations(
        models, 
        beh_scaled, ass_scaled, ctx_scaled,
        behavioral_features, association_features, contextual_features,
        weights
    )
    
    return {
        'address': address,
        'risk_score': float(final_score),
        'prediction': prediction,
        'threshold': threshold,
        'dimensions': {
            'behavioral': {
                'score': float(beh_score),
                'contribution': float(weights['behavioral'] * beh_score),
                'weight': float(weights['behavioral']),
                'features': dict(zip(BEHAVIORAL_FEATURES, behavioral_features)),
                'shap': shap_explanations['behavioral']
            },
            'association': {
                'score': float(ass_score),
                'contribution': float(weights['association'] * ass_score),
                'weight': float(weights['association']),
                'features': dict(zip(ASSOCIATION_FEATURES, association_features)),
                'shap': shap_explanations['association']
            },
            'contextual': {
                'score': float(ctx_score),
                'contribution': float(weights['contextual'] * ctx_score),
                'weight': float(weights['contextual']),
                'features': dict(zip(CONTEXTUAL_FEATURES, contextual_features)),
                'shap': shap_explanations['contextual']
            }
        },
        'metadata': {
            'total_transactions': len(transactions_df) if not transactions_df.empty else 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }


def print_results(result):
    """Print formatted results with SHAP explanations"""
    print(f"\n{'='*80}")
    print(f"RISK ASSESSMENT RESULTS")
    print(f"{'='*80}")
    print(f"\nWallet Address: {result['address']}")
    print(f"Timestamp: {result['metadata']['timestamp']}")
    print(f"Total Transactions: {result['metadata']['total_transactions']}")
    
    print(f"\n{'-'*80}")
    print(f"RISK SCORE: {result['risk_score']:.4f}")
    print(f"PREDICTION: {result['prediction']}")
    print(f"Threshold: {result['threshold']:.2f}")
    print(f"{'-'*80}")
    
    print(f"\n{'-'*80}")
    print(f"DIMENSION BREAKDOWN")
    print(f"{'-'*80}")
    
    for dim_name in ['behavioral', 'association', 'contextual']:
        dim = result['dimensions'][dim_name]
        print(f"\n{dim_name.upper()} Dimension:")
        print(f"  Score: {dim['score']:.4f}")
        print(f"  Contribution: {dim['contribution']:.4f}")
        print(f"  Weight: {dim['weight']:.2f}")
        
        # Show SHAP explanations if available
        if dim['shap']['top_features']:
            print(f"\n  Top Contributing Features (SHAP Analysis):")
            for i, feat in enumerate(dim['shap']['top_features'], 1):
                feat_val = feat['feature_value']
                if isinstance(feat_val, float):
                    if feat_val < 0.01:
                        feat_str = f"{feat_val:.6f}"
                    else:
                        feat_str = f"{feat_val:.2f}"
                else:
                    feat_str = str(feat_val)
                print(f"    {i}. {feat['feature']}")
                print(f"       Value: {feat_str}")
                print(f"       SHAP: {feat['shap_value']:+.4f} ({feat['impact']})")
        else:
            print(f"  (Contribution below threshold - SHAP not computed)")





# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{'='*80}")
    print(f"WALLET RISK SCORING SYSTEM")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get wallet address from command line
    if len(sys.argv) < 2:
        print("Usage: python wallet_scoring.py <wallet_address>")
        print("Example: python wallet_scoring.py 0x1234567890abcdef1234567890abcdef12345678")
        sys.exit(1)
    
    address = sys.argv[1]
    
    # Validate address format
    if not address.startswith('0x') or len(address) != 42:
        print(f"Error: Invalid Ethereum address format. Expected 42 characters starting with '0x'")
        sys.exit(1)
    
    # Load models and blacklist
    models = load_models()
    blacklist_set = load_blacklist()
    
    # Score wallet
    result = score_wallet(address, models, blacklist_set)
    
    # Print results
    print_results(result)


if __name__ == "__main__":
    main()
