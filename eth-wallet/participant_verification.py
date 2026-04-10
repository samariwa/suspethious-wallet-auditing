import requests
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import warnings
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import RandomOverSampler
import xgboost as xgb
import pickle
import shap

# Load environment variables from parent directory
parent_dir = Path(__file__).parent.parent
load_dotenv(parent_dir / '.env')

BASE_URL = "https://api.etherscan.io/api"

def fetch_wallet_transactions(address: str) -> list:
    """
    Fetches all normal transactions for an Ethereum wallet from Etherscan.
    Returns a list of transactions as dictionaries (ready for feature extraction).
    """
    try:
        url = (
            f"{BASE_URL}?module=account&action=txlist"
            f"&address={address}&startblock=0&endblock=99999999"
            f"&sort=asc&apikey={os.environ['ETHERSCAN_API_KEY']}"
        )
        response = requests.get(url)
        data = response.json()

        if data["status"] != "1":
            # If no transactions found, treat as normal account (not flagged)
            if data["message"].lower().startswith("no transactions"):
                return []
            raise ValueError(f"Error from Etherscan: {data['message']}")

        return data["result"]

    except Exception as e:
        # Only raise if not the 'no transactions found' case
        if "no transactions found" in str(e).lower():
            return []
        raise RuntimeError(f"Failed to fetch transactions: {e}")

def extract_features_from_etherscan(tx_list, address):
    if not tx_list:
        # Return default features for a new/empty account
        # These features should match the columns used in training
        features = pd.DataFrame([{k: 0 for k in [
            "Avg min between sent tnx", "Avg min between received tnx", "Time Diff between first and last (Mins)",
            "Sent tnx", "Received Tnx", "Number of Created Contracts", "Unique Received From Addresses",
            "Unique Sent To Addresses", "min value received", "max value received ", "avg val received",
            "min val sent", "max val sent", "avg val sent", "min value sent to contract",
            "max val sent to contract", "avg value sent to contract", "total transactions (including tnx to create contract",
            "total Ether sent", "total ether received", "total ether balance"
        ]}])
        features["is_new_account"] = 1  # Add a flag for new accounts if not present in training, or just use zeros
        return features.drop(columns=["is_new_account"], errors="ignore")

    df = pd.DataFrame(tx_list)
    df['timestamp'] = pd.to_datetime(df['timeStamp'].astype(int), unit='s')
    df['value_eth'] = df['value'].astype(float) / 1e18
    df = df.sort_values('timestamp')

    # Basic filters
    sent = df[df['from'].str.lower() == address.lower()]
    received = df[df['to'].str.lower() == address.lower()]

    # Times
    avg_time_sent = sent['timestamp'].diff().dt.total_seconds().dropna().mean() / 60 if len(sent) > 1 else 0
    avg_time_received = received['timestamp'].diff().dt.total_seconds().dropna().mean() / 60 if len(received) > 1 else 0
    time_diff_total = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60

    # Value stats
    min_received = received['value_eth'].min() if not received.empty else 0
    max_received = received['value_eth'].max() if not received.empty else 0
    avg_received = received['value_eth'].mean() if not received.empty else 0

    min_sent = sent['value_eth'].min() if not sent.empty else 0
    max_sent = sent['value_eth'].max() if not sent.empty else 0
    avg_sent = sent['value_eth'].mean() if not sent.empty else 0

    # Unique address counts
    uniq_received_from = received['from'].nunique()
    uniq_sent_to = sent['to'].nunique()

    # Contract interactions
    sent_contracts = sent[sent['input'] != '0x']
    avg_val_sent_to_contract = sent_contracts['value_eth'].mean() if not sent_contracts.empty else 0
    min_val_sent_to_contract = sent_contracts['value_eth'].min() if not sent_contracts.empty else 0
    max_val_sent_to_contract = sent_contracts['value_eth'].max() if not sent_contracts.empty else 0

    # Aggregates
    total_tx = len(df)
    total_eth_sent = sent['value_eth'].sum()
    total_eth_received = received['value_eth'].sum()
    total_balance = total_eth_received - total_eth_sent

    return pd.DataFrame([{
        "Avg min between sent tnx": avg_time_sent,
        "Avg min between received tnx": avg_time_received,
        "Time Diff between first and last (Mins)": time_diff_total,
        "Sent tnx": len(sent),
        "Received Tnx": len(received),
        "Number of Created Contracts": sum((sent['to'] == '') | (sent['to'].isna())),
        "Unique Received From Addresses": uniq_received_from,
        "Unique Sent To Addresses": uniq_sent_to,
        "min value received": min_received,
        "max value received ": max_received,
        "avg val received": avg_received,
        "min val sent": min_sent,
        "max val sent": max_sent,
        "avg val sent": avg_sent,
        "min value sent to contract": min_val_sent_to_contract,
        "max val sent to contract": max_val_sent_to_contract,
        "avg value sent to contract": avg_val_sent_to_contract,
        "total transactions (including tnx to create contract": total_tx,
        "total Ether sent": total_eth_sent,
        "total ether received": total_eth_received,
        "total ether balance": total_balance
    }])

def train_model():
    df = pd.read_csv('transaction_dataset.csv', index_col=0)
    categories = df.select_dtypes('O').columns.astype('category')
    df.drop(df[categories], axis=1, inplace=True)
    df.fillna(df.median(), inplace=True)
    no_var = df.var() == 0
    df.drop(df.var()[no_var].index, axis = 1, inplace = True)
    drop = ['Index', 'total ether sent contracts', ' Total ERC20 tnxs',
    ' ERC20 total Ether received',
    ' ERC20 total ether sent',
    ' ERC20 total Ether sent contract',
    ' ERC20 uniq sent addr',
    ' ERC20 uniq rec addr',
    ' ERC20 uniq rec contract addr',
    ' ERC20 min val rec',
    ' ERC20 max val rec',
    ' ERC20 avg val rec',
    ' ERC20 min val sent',
    ' ERC20 max val sent',
    ' ERC20 avg val sent',
    ' ERC20 uniq sent token name',
    ' ERC20 uniq rec token name',
    ' ERC20 uniq sent addr.1']
    df.drop(drop, axis=1, inplace=True)
    y = df.iloc[:, 0]
    X = df.iloc[:, 1:]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)
    norm = PowerTransformer()
    norm_train_f = norm.fit_transform(X_train)
    norm_df = pd.DataFrame(norm_train_f, columns=X_train.columns)
    oversample = RandomOverSampler(random_state=42)
    x_tr_resample, y_tr_resample = oversample.fit_resample(norm_train_f, y_train)
    xgb_c = xgb.XGBClassifier(random_state=42)
    xgb_c.fit(x_tr_resample, y_tr_resample)
    # Save the normalizer and model (overwrite or create if not exist)
    with open('scam_model.pkl', 'wb') as f:
        pickle.dump(xgb_c, f)
    with open('scam_normalizer.pkl', 'wb') as f:
        pickle.dump(norm, f)
    # Optionally, print test accuracy
    norm_test_f = norm.transform(X_test)
    preds_xgb = xgb_c.predict(norm_test_f)
    print('Test accuracy:', (preds_xgb == y_test).mean())


def predict_scam(features):
    """
    features: pd.DataFrame with the same columns as used in training (single row)
    Returns: 'flagged' or 'not flagged'
    """
    # If all features are zero, treat as normal (not flagged)
    if (features == 0).all(axis=None):
        return 'not flagged', []
    # Load the normalizer and model
    with open('scam_normalizer.pkl', 'rb') as f:
        norm = pickle.load(f)
    with open('scam_model.pkl', 'rb') as f:
        xgb_c = pickle.load(f)
    norm_test_f = norm.transform(features)
    preds_xgb = xgb_c.predict(norm_test_f)
    verdict = 'flagged' if preds_xgb[0] == 1 else 'not flagged'
    if verdict == 'flagged':
        import shap
        explainer = shap.TreeExplainer(xgb_c)
        shap_values = explainer.shap_values(norm_test_f)
        feature_contributions = dict(zip(features.columns, shap_values[0]))
        sorted_contrib = sorted(feature_contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        top_features = sorted_contrib[:3]  # Top 3 contributors
        return verdict, top_features
    else:
        return verdict, []

def predict_address_scam(address: str):
    """
    Given an Ethereum address, fetches transactions, extracts features, and predicts scam status.
    Returns: 'flagged' or 'not flagged'
    """
    txs = fetch_wallet_transactions(address)
    features = extract_features_from_etherscan(txs, address)
    return predict_scam(features)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        print("Training scam detection model...")
        train_model()
        print("Model and normalizer saved as scam_model.pkl and scam_normalizer.pkl.")
    else:
        address = "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae"
        transactions = fetch_wallet_transactions(address)
        features = extract_features_from_etherscan(transactions, address)
        print(predict_scam(features))



