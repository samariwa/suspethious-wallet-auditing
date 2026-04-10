from flask import Flask, jsonify, request
from flask_cors import CORS
from wallet_test import get_wallet_info, get_wallet_balance, list_tokens, get_network, send_transaction
from wallet_risk_assessment import assess_wallet_risk, get_risk_explanation
from langchain_agent import run_scam_agent
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route("/api/wallet")
def wallet():
    info = get_wallet_info()
    lines = info.splitlines()
    address = lines[0].split(": ", 1)[1] if len(lines) > 0 else ""
    pub_key = lines[1].split(": ", 1)[1] if len(lines) > 1 else ""
    return jsonify({"address": address, "pub_key": pub_key})

@app.route("/api/balance")
def balance():
    bal = get_wallet_balance()
    return jsonify({"balance": bal})

@app.route("/api/tokens")
def tokens():
    return jsonify({"tokens": list_tokens()})

@app.route("/api/network")
def network():
    return jsonify({"network": get_network()})

def detect_address_type(address):
    """
    Detect whether an Ethereum address is a wallet (EOA) or a smart contract
    using Etherscan API — no Web3 connection required.

    Two-stage approach handles all contract types:
      1. getsourcecode: status=1 → any contract Etherscan has indexed (verified or not)
      2. txlist first tx:  to="" + contractAddress==address → catches unverified
         and self-destructed contracts (bytecode gone, but creation tx persists)

    Returns:
        str: "Smart Contract" or "Wallet"
    """
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
    ETHERSCAN_URL = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api")

    # --- Check 1: getsourcecode -------------------------------------------
    # Etherscan returns status=1 for ALL addresses (including EOAs), so we
    # must check ContractName. A non-empty ContractName means Etherscan has
    # indexed the contract (verified or self-destructed with a known name).
    # EOAs always have ContractName="" and ABI="Contract source code not verified".
    try:
        resp = requests.get(ETHERSCAN_URL, params={
            "chainid": 1,
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": ETHERSCAN_API_KEY,
        }, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("result"):
            contract_name = data["result"][0].get("ContractName", "")
            if contract_name:  # Non-empty name = definitely a contract
                return "Smart Contract"
    except Exception:
        pass

    # --- Check 2: contract creation transaction ----------------------------
    # Every smart contract has a creation tx where `to` is empty and
    # `contractAddress` equals the deployed address. This works even when
    # the contract has self-destructed (bytecode is gone but the tx remains).
    try:
        resp = requests.get(ETHERSCAN_URL, params={
            "chainid": 1,
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "page": 1,
            "offset": 1,
            "apikey": ETHERSCAN_API_KEY,
        }, timeout=10)
        data = resp.json()
        if data.get("status") == "1" and data.get("result"):
            first_tx = data["result"][0]
            if (first_tx.get("to") == "" and
                    first_tx.get("contractAddress", "").lower() == address.lower()):
                return "Smart Contract"
    except Exception:
        pass

    return "Wallet"


def fetch_sender_history(sender_address):
    """
    Fetch sender's own transaction history from Etherscan and compute
    their historical average ETH sent per transaction.

    Returns:
        tuple: (avg_sent_eth, sent_tx_count)
            avg_sent_eth  — average ETH sent per sent transaction (float)
            sent_tx_count — number of sent transactions found (int)
        Returns (None, 0) on failure or missing address.
    """
    if not sender_address:
        return None, 0

    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
    ETHERSCAN_URL = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api")

    try:
        resp = requests.get(ETHERSCAN_URL, params={
            "chainid": 1,
            "module": "account",
            "action": "txlist",
            "address": sender_address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": ETHERSCAN_API_KEY,
        }, timeout=15)
        data = resp.json()

        if data.get("status") != "1" or not data.get("result"):
            return None, 0

        txns = data["result"]
        sender_lower = sender_address.lower()

        # Only outgoing transactions (from sender)
        sent_txns = [tx for tx in txns if tx.get("from", "").lower() == sender_lower]
        sent_tx_count = len(sent_txns)

        if sent_tx_count == 0:
            return None, 0

        total_eth_sent = sum(int(tx.get("value", 0)) for tx in sent_txns) / 1e18
        avg_sent_eth = total_eth_sent / sent_tx_count

        return avg_sent_eth, sent_tx_count

    except Exception:
        return None, 0


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    address = data.get("address")
    amount = data.get("amount")        # Transaction amount in ETH
    sender_address = data.get("sender_address")  # Sender's own wallet address
    if not address:
        return jsonify({"error": "Missing address"}), 400
    try:
        # Get the detailed risk assessment
        results = assess_wallet_risk(address)
        
        if "error" in results:
            return jsonify({"error": results["error"]}), 500
        
        # Detect address type (wallet vs smart contract)
        address_type = detect_address_type(address)
        
        # Calculate impact category if amount is provided
        impact_data = None
        if amount:
            try:
                amount_float = float(amount)
                # Fetch sender history for relative financial impact threshold
                sender_avg_eth, sender_tx_count = fetch_sender_history(sender_address)
                impact_data = calculate_impact_category(
                    risk_score=results['risk_score'],
                    transaction_amount=amount_float,
                    address_type=address_type,
                    threshold=results['threshold'],
                    sender_avg_eth=sender_avg_eth,
                    sender_tx_count=sender_tx_count
                )
            except (ValueError, TypeError):
                pass  # If amount is invalid, skip impact calculation
        
        # Use LangChain agent with OpenAI for natural language explanation
        explanation = run_scam_agent(address, address_type)
        
        response_data = {
            "result": explanation,
            "risk_assessment": results,
            "address_type": address_type
        }
        
        if impact_data:
            response_data["impact_assessment"] = impact_data
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def calculate_impact_category(risk_score, transaction_amount, address_type, threshold,
                              sender_avg_eth=None, sender_tx_count=0):
    """
    Calculate impact category based on Likelihood, Financial Impact, and Transaction Type.

    Financial impact uses a hybrid threshold strategy:
      - Relative (preferred): if sender has >= 10 sent transactions, compare
        current amount against 3x their historical average sent per transaction.
      - Absolute (fallback): if sender history is unavailable or sparse (<10 txns),
        fall back to dataset median of 2.07 ETH.

    Args:
        risk_score:        Model's risk score (0-1)
        transaction_amount: Transaction amount in ETH
        address_type:      "Smart Contract" or "Wallet"
        threshold:         Model's classification threshold
        sender_avg_eth:    Sender's historical avg ETH sent per txn (None if unknown)
        sender_tx_count:   Number of sent transactions in sender's history

    Returns:
        dict: Impact assessment with category and explanation
    """
    # Absolute fallback threshold (dataset median)
    ABSOLUTE_FINANCIAL_THRESHOLD = 2.07  # ETH
    # Relative threshold: flag if current amount >= this multiple of sender avg
    NOVELTY_MULTIPLIER = 3
    # Minimum sent transactions required to trust the relative threshold
    MIN_TX_FOR_RELATIVE = 10

    # Determine which threshold to apply
    use_relative = (
        sender_avg_eth is not None
        and sender_tx_count >= MIN_TX_FOR_RELATIVE
        and sender_avg_eth > 0
    )

    if use_relative:
        effective_threshold = NOVELTY_MULTIPLIER * sender_avg_eth
        threshold_method = "relative"
    else:
        effective_threshold = ABSOLUTE_FINANCIAL_THRESHOLD
        threshold_method = "absolute"

    # Step 1: Classify Likelihood
    likelihood = "High" if risk_score >= threshold else "Low"

    # Step 2: Classify Financial Impact
    financial_impact = "High" if transaction_amount >= effective_threshold else "Low"

    # Step 3: Classify Transaction Type
    tx_type = "Contract" if address_type == "Smart Contract" else "Wallet"

    # Step 4: Decision matrix
    if likelihood == "High" and financial_impact == "High":
        if tx_type == "Contract":
            category = "Critical"
            explanation = (
                "HIGH RISK smart contract interaction with HIGH financial exposure. "
                "This transaction involves code execution at the destination address, "
                "increasing the potential for fund loss. Immediate review recommended."
            )
        else:
            category = "High"
            explanation = (
                "HIGH RISK wallet transaction with HIGH financial exposure. "
                "The recipient wallet shows strong fraud indicators and the amount "
                "exceeds the typical transaction threshold. Manual verification strongly advised."
            )
    elif likelihood == "High" and financial_impact == "Low":
        if tx_type == "Contract":
            category = "High"
            explanation = (
                "HIGH RISK smart contract interaction. Although the amount is below the "
                "typical threshold, smart contract interactions can execute hidden logic "
                "such as unlimited token approvals. Proceed with caution."
            )
        else:
            category = "Moderate"
            explanation = (
                "HIGH RISK wallet with LOW financial exposure. "
                "The recipient shows fraud indicators but the amount is small. "
                "Monitor this wallet and avoid further transactions."
            )
    elif likelihood == "Low" and financial_impact == "High":
        if tx_type == "Contract":
            category = "Moderate"
            explanation = (
                "LOW RISK smart contract with HIGH financial exposure. "
                "No fraud indicators detected, but large contract interactions carry "
                "inherent execution risk. Verify the contract is audited before proceeding."
            )
        else:
            category = "Low"
            explanation = (
                "LOW RISK wallet transaction with HIGH financial exposure. "
                "No fraud indicators detected on the recipient. Verify the recipient "
                "address carefully given the transaction size."
            )
    else:  # likelihood == "Low" and financial_impact == "Low"
        if tx_type == "Contract":
            category = "Low"
            explanation = (
                "LOW RISK smart contract interaction with LOW financial exposure. "
                "No fraud indicators detected and the amount is small. "
                "Standard contract interaction caution applies."
            )
        else:
            category = "Minimal"
            explanation = (
                "LOW RISK wallet transaction with LOW financial exposure. "
                "No fraud indicators detected. Safe to proceed."
            )

    return {
        "impact_category": category,
        "explanation": explanation,
        "factors": {
            "likelihood": likelihood,
            "financial_impact": financial_impact,
            "transaction_type": tx_type
        },
        "thresholds": {
            "risk_threshold": threshold,
            "financial_threshold_eth": effective_threshold,
            "financial_threshold_method": threshold_method,
            "sender_avg_eth": sender_avg_eth,
            "sender_tx_count": sender_tx_count
        },
        "values": {
            "risk_score": risk_score,
            "transaction_amount_eth": transaction_amount,
            "address_type": address_type
        }
    }

@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json()
    to_address = data.get("to_address")
    amount = data.get("amount")
    passphrase = data.get("passphrase")
    if not to_address or not amount or not passphrase:
        return jsonify({"error": "Missing to_address, amount, or passphrase"}), 400
    try:
        result = send_transaction(to_address, amount, passphrase)
        if "Error" in result or "error" in result.lower():
            return jsonify({"error": result}), 400
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5001, debug=True)
