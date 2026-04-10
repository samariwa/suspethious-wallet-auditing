"""
Wallet Risk Assessment Module
Uses the ensemble model from wallet_scoring.py for fraud detection
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import wallet_scoring
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Change to parent directory for relative paths to work
original_cwd = os.getcwd()
os.chdir(parent_dir)

from wallet_scoring import (
    score_wallet,
    load_models,
    load_blacklist,
    BEHAVIORAL_FEATURES,
    ASSOCIATION_FEATURES,
    CONTEXTUAL_FEATURES
)

# Load models once at module initialization
print("Loading ensemble models...")
models = load_models()
blacklist = load_blacklist()
print(f"✓ Models loaded, {len(blacklist)} blacklisted addresses in database")

# Restore original working directory
os.chdir(original_cwd)

def assess_wallet_risk(address: str) -> dict:
    """
    Assess fraud risk for an Ethereum wallet address using the ensemble model.
    
    Args:
        address: Ethereum wallet address to assess
        
    Returns:
        dict: Risk assessment results containing:
            - address: The wallet address
            - risk_score: Overall risk score (0-1)
            - prediction: 'HIGH RISK' or 'LOW RISK'
            - threshold: Classification threshold
            - dimensions: Individual dimension scores and contributions
            - shap_explanations: SHAP values for explainability
            - metadata: Transaction counts and other metadata
    """
    try:
        results = score_wallet(address, models, blacklist)
        return results
    except Exception as e:
        return {
            "error": str(e),
            "address": address,
            "risk_score": None,
            "prediction": "ERROR"
        }

def get_risk_explanation(results: dict) -> str:
    """
    Generate a human-readable explanation of the risk assessment.
    
    Args:
        results: Results dict from assess_wallet_risk()
        
    Returns:
        str: Plain English explanation
    """
    if "error" in results:
        return f"Error assessing wallet: {results['error']}"
    
    address = results['address']
    risk_score = results['risk_score']
    prediction = results['prediction']
    
    # Build explanation
    explanation = f"Wallet {address} has been assessed as {prediction}.\n"
    explanation += f"Overall Risk Score: {risk_score:.4f} (threshold: {results['threshold']})\n\n"
    
    # Dimension breakdown
    explanation += "Risk Dimension Analysis:\n"
    for dim_name, dim_data in results['dimensions'].items():
        score = dim_data['score']
        contribution = dim_data['contribution']
        weight = dim_data['weight']
        
        explanation += f"\n{dim_name}:\n"
        explanation += f"  Score: {score:.4f} | Weight: {weight:.2f} | Contribution: {contribution:.4f}\n"
        
        # Add SHAP explanations if available
        if 'shap_top_features' in dim_data and dim_data['shap_top_features']:
            explanation += f"  Key factors:\n"
            for feat in dim_data['shap_top_features'][:3]:
                direction = "increases" if feat['shap_value'] > 0 else "decreases"
                explanation += f"    • {feat['feature']}: {feat['value']:.4f} ({direction} risk)\n"
    
    # Add metadata
    if 'metadata' in results:
        meta = results['metadata']
        explanation += f"\nTransaction History:\n"
        explanation += f"  Total Transactions: {meta.get('total_transactions', 'N/A')}\n"
        if 'blacklist_interactions' in meta:
            bl = meta['blacklist_interactions']
            explanation += f"  Blacklist Interactions: {bl['to'] + bl['from']} transactions\n"
    
    return explanation

def predict_scam_simple(address: str) -> tuple:
    """
    Simple interface compatible with the old predict_scam function.
    
    Args:
        address: Ethereum wallet address
        
    Returns:
        tuple: (verdict, top_features) where verdict is 'flagged' or 'not flagged'
               and top_features is a list of (feature_name, shap_value) tuples
    """
    results = assess_wallet_risk(address)
    
    if "error" in results:
        return ("not flagged", [])
    
    verdict = "flagged" if results['prediction'] == "HIGH RISK" else "not flagged"
    
    # Extract top features from SHAP explanations
    top_features = []
    for dim_name, dim_data in results['dimensions'].items():
        if 'shap_top_features' in dim_data and dim_data['shap_top_features']:
            for feat in dim_data['shap_top_features'][:3]:
                top_features.append((feat['feature'], feat['shap_value']))
    
    # Sort by absolute SHAP value and take top 5
    top_features.sort(key=lambda x: abs(x[1]), reverse=True)
    top_features = top_features[:5]
    
    return (verdict, top_features)
