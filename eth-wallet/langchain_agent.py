import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory
parent_dir = Path(__file__).parent.parent
load_dotenv(parent_dir / '.env')

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from wallet_risk_assessment import assess_wallet_risk

# Initialize OpenAI LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.3)

# Feature explanations - simplified and user-friendly
DIMENSION_CONTEXT = {
    "behavioral": {
        "description": "analyzes the wallet's transaction patterns, frequency, timing, and volume",
        "features": {
            "Avg min between sent tnx": "how frequently the wallet sends transactions",
            "Avg min between received tnx": "how frequently the wallet receives transactions",
            "Time Diff between first and last (Mins)": "how long the wallet has been active",
            "Sent tnx": "total number of transactions sent",
            "Received Tnx": "total number of transactions received",
            "Number of Created Contracts": "number of smart contracts deployed",
            "total transactions (including tnx to create contract)": "overall transaction activity",
            "total Ether sent": "total amount of ETH sent out",
            "total ether received": "total amount of ETH received"
        }
    },
    "association": {
        "description": "checks if the wallet has interacted with known malicious addresses",
        "features": {
            "No. of txns from blacklisted addresses": "transactions received from flagged wallets",
            "No. of txns to blacklisted addresses": "transactions sent to flagged wallets",
            "Total ether sent to blacklisted addresses": "amount of ETH sent to suspicious wallets",
            "Ratio of total sent to blacklisted addresses": "proportion of funds sent to risky addresses",
            "Total ether received from blacklisted addresses": "amount of ETH received from suspicious wallets",
            "Ratio of total received from blacklisted addresses": "proportion of funds from risky sources"
        }
    },
    "contextual": {
        "description": "examines transaction execution quality, gas usage, and failure patterns",
        "features": {
            "gas_price_std_dev": "consistency of gas prices used",
            "total_failed_txns": "number of failed transactions",
            "failed_contract_interaction_ratio": "percentage of failed smart contract calls",
            "avg_gas_price_gwei": "average gas price paid"
        }
    }
}

def generate_natural_language_explanation(risk_results: dict, address_type: str = "Wallet") -> str:
    """
    Uses OpenAI to generate a natural language explanation of the risk assessment.
    Focuses only on dimensions that contributed significantly (above threshold).
    """
    
    # Check if wallet is high risk
    is_high_risk = risk_results['prediction'] == 'HIGH RISK'
    risk_score = risk_results['risk_score']
    address = risk_results['address']
    entity_label = "smart contract" if address_type == "Smart Contract" else "wallet"
    
    if not is_high_risk:
        return f"This {entity_label} appears legitimate. Risk score: {risk_score:.2%}"
    CONTRIBUTION_THRESHOLD = 0.15
    significant_dimensions = []
    
    for dim_name, dim_data in risk_results['dimensions'].items():
        contribution = dim_data['contribution']
        if contribution >= CONTRIBUTION_THRESHOLD:
            # Get top SHAP features that increase risk (positive SHAP values)
            top_features = []
            if 'shap' in dim_data and 'top_features' in dim_data['shap']:
                for feat_data in dim_data['shap']['top_features']:
                    if feat_data['shap_value'] > 0:  # Only features that increase risk
                        top_features.append({
                            'name': feat_data['feature'],
                            'value': feat_data['feature_value'],
                            'shap': feat_data['shap_value'],
                            'description': DIMENSION_CONTEXT[dim_name]['features'].get(feat_data['feature'], feat_data['feature'])
                        })
                
                # Sort by SHAP value and take top 3
                top_features.sort(key=lambda x: abs(x['shap']), reverse=True)
                top_features = top_features[:3]
            
            significant_dimensions.append({
                'name': dim_name.upper(),
                'description': DIMENSION_CONTEXT[dim_name]['description'],
                'score': dim_data['score'],
                'contribution': contribution,
                'top_features': top_features
            })
    
    # Build context for LLM
    context = f"""
You are analyzing an Ethereum {entity_label} for fraud risk. The address is {address}.

The AI model has flagged this {entity_label} as HIGH RISK with an overall risk score of {risk_score:.2%}.

Here are the risk dimensions that contributed significantly to this classification:

"""
    
    for dim in significant_dimensions:
        context += f"\n{dim['name']} DIMENSION ({dim['contribution']:.1%} contribution):\n"
        context += f"This dimension {dim['description']}.\n"
        context += f"Risk score for this dimension: {dim['score']:.2%}\n"
        
        if dim['top_features']:
            context += "\nKey warning signs:\n"
            for feat in dim['top_features']:
                context += f"- {feat['description']}: {feat['value']}\n"
        context += "\n"
    
    # Create prompt for OpenAI
    entity_display = "Smart Contract" if address_type == "Smart Contract" else "Wallet"
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a fraud analyst explaining Ethereum {entity_label} risk assessments to everyday people with no technical background.
Your job is to explain WHY a {entity_label} was flagged as high risk in plain, conversational language — as if you were explaining it to a friend.

Guidelines:
- Use simple, everyday language. Imagine explaining this to someone who has never heard of blockchain.
- Always refer to the subject as a "{entity_label}" (never use the word "{'wallet' if entity_label == 'smart contract' else 'contract'}").
- NEVER use internal model terms like "Association Dimension", "Behavioral Dimension", "Contextual Dimension", "dimension", "model", "SHAP", "feature", or any ML/technical terminology.
- Instead of saying "the Association Dimension flagged X", say things like "it has been sending and receiving funds to known fraudsters" or "it has connections to addresses flagged for scams".
- Instead of saying "the Behavioral Dimension", say things like "the way it moves money is unusual" or "the transaction patterns look suspicious".
- Focus on what the {entity_label} actually DID that is suspicious — the real-world behaviour, not the system internals.
- Be concise: 1 paragraph total, 3-5 sentences. No bullet points. No headers.
- Tone: calm, clear, and helpful. Not alarmist."""),
        ("human", """Based on this risk analysis, write a short plain-English explanation of why this {entity_label} was flagged as high risk:

{{context}}

Remember: no technical terms, no dimension names, no model references. Just explain the suspicious behaviour in plain language a regular person would understand.""".format(entity_label=entity_label))
    ])
    
    # Generate explanation using OpenAI
    try:
        chain = prompt | llm
        response = chain.invoke({"context": context})
        explanation = response.content
        
        return f"HIGH RISK {entity_display.upper()} DETECTED\n\n{explanation}"
    
    except Exception as e:
        # Fallback to simple explanation if OpenAI fails
        fallback = f"This {entity_label} has been flagged as HIGH RISK (score: {risk_score:.2%}).\n\n"
        fallback += "Concerning factors:\n"
        for dim in significant_dimensions:
            fallback += f"- {dim['name']}: {dim['description']} (Risk: {dim['score']:.0%})\n"
        fallback += f"\nError generating detailed explanation: {str(e)}"
        return fallback


# Simplified prefix for backwards compatibility
PREFIX = (
    "You are an Ethereum wallet scam analysis assistant. "
    "You use a machine learning model to flag scam wallets based on transaction features. "
    "When a wallet is flagged, you will explain the top contributing features in simple English. "
    "Here is what the output means: "
    "- 'flagged': The address is likely a scam based on its transaction patterns. "
    "- 'not flagged': The address appears normal. "
    "- The 'top contributing features' are the most important reasons the model flagged the address. "
    "For each feature, explain what it means in the context of Ethereum transactions, using the following descriptions: "
    "Avg min between sent tnx: Average time between sent transactions for account in minutes. "
    "Avg min between received tnx: Average time between received transactions for account in minutes. "
    "Time Diff between first and last (Mins): Time difference between the first and last transaction. "
    "Sent tnx: Total number of sent normal transactions. "
    "Received Tnx: Total number of received normal transactions. "
    "Number of Created Contracts: Total number of created contract transactions. "
    "Unique Received From Addresses: Total unique addresses from which account received transactions. "
    "Unique Sent To Addresses: Total unique addresses to which account sent transactions. "
    "min value received: Minimum value in Ether ever received. "
    "max value received : Maximum value in Ether ever received. "
    "avg val received: Average value in Ether ever received. "
    "min val sent: Minimum value of Ether ever sent. "
    "max val sent: Maximum value of Ether ever sent. "
    "avg val sent: Average value of Ether ever sent. "
    "min value sent to contract: Minimum value of Ether sent to a contract. "
    "max val sent to contract: Maximum value of Ether sent to a contract. "
    "avg value sent to contract: Average value of Ether sent to contracts. "
    "total transactions (including tnx to create contract: Total number of transactions. "
    "total Ether sent: Total Ether sent for account address. "
    "total ether received: Total Ether received for account address. "
    "total ether balance: Total Ether balance following enacted transactions. "
    "If a feature is not listed, do your best to explain it based on its name. "
    "Be clear and concise."
)

def run_scam_agent(address: str, address_type: str = "Wallet") -> str:
    """
    Analyzes a wallet/contract and returns a natural language explanation using OpenAI.
    """
    try:
        # Get risk assessment from ensemble model
        risk_results = assess_wallet_risk(address)
        
        if "error" in risk_results:
            return f"SuspETHious: Error analyzing address: {risk_results['error']}"
        
        # Generate natural language explanation using OpenAI
        explanation = generate_natural_language_explanation(risk_results, address_type)
        
        return f"SuspETHious: {explanation}"
    
    except Exception as e:
        return f"SuspETHious: Error analyzing address: {str(e)}"
