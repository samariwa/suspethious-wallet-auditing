import React, { useEffect, useState, useRef } from "react";
import "./App.css";

function Modal({
  open,
  verdict,
  onClose,
  onConfirm,
  sending,
  sendResult,
  error,
  passphrase,
  setPassphrase,
  details,
  riskScore,
  addressType,
  impactCategory,
  impactExplanation,
}) {
  const [showDetails, setShowDetails] = useState(false);
  // Detect high risk verdict - updated for new OpenAI format
  const isHighRisk =
    verdict &&
    (verdict.toLowerCase().includes("high risk") || verdict.includes("⚠️"));

  const isVerified =
    verdict &&
    (verdict.toLowerCase().includes("appears legitimate") ||
      verdict.includes("✅") ||
      verdict.toLowerCase().includes("recipient verified"));

  // Extract summary and details
  let summary = verdict;
  let detailsText = details || "";

  if (isHighRisk) {
    // For high risk, extract first line as summary
    const lines = verdict.split("\n");
    summary = lines[0] || verdict;
    detailsText = verdict;
  } else if (isVerified) {
    // For verified/low risk wallets
    summary = verdict.split("\n")[0] || verdict;
    detailsText = "";
  }
  return !open ? null : (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(10,35,66,0.18)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
          padding: "2.2rem 2.5rem",
          minWidth: 420,
          maxWidth: 480,
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            fontWeight: 600,
            fontSize: 18,
            color: isHighRisk ? "#e74c3c" : isVerified ? "#27ae60" : "#222",
            fontFamily: "Menlo, Monaco, 'Fira Mono', monospace",
            marginBottom: 18,
            minHeight: 60,
            width: "100%",
            whiteSpace: "pre-line",
            textAlign: "center",
          }}
        >
          {summary}
        </div>
        {isHighRisk && (
          <div style={{ marginBottom: 12 }}>
            <button
              onClick={() => setShowDetails((v) => !v)}
              style={{
                background: "none",
                border: "none",
                color: "#2980b9",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: 15,
                textDecoration: "underline",
              }}
            >
              {showDetails ? "Hide Details" : "View More Details"}
            </button>
          </div>
        )}
        {isHighRisk && showDetails && (
          <div
            style={{
              width: "100%",
              marginBottom: 18,
              minHeight: 60,
              textAlign: "left",
            }}
          >
            <Typewriter text={detailsText} />
          </div>
        )}

        {/* Risk Assessment Summary */}
        {(riskScore || addressType || impactCategory) && (
          <div
            style={{
              width: "100%",
              marginBottom: 18,
              padding: "1rem",
              background: "#f8fafd",
              borderRadius: 8,
              border: "1px solid #e1e8ed",
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 8, color: "#222", fontSize: 15 }}>
              Risk Assessment
            </div>
            {riskScore && (
              <div style={{ marginBottom: 6, fontSize: 14, color: "#555" }}>
                <span style={{ fontWeight: 600 }}>Risk Score:</span> {riskScore}%
              </div>
            )}
            {addressType && (
              <div style={{ marginBottom: 6, fontSize: 14, color: "#555" }}>
                <span style={{ fontWeight: 600 }}>Address Type:</span>{" "}
                <span style={{
                  fontWeight: 600,
                  color: addressType === "Smart Contract" ? "#e67e22" : "#2980b9"
                }}>
                  {addressType}
                </span>
              </div>
            )}
            {impactCategory && (
              <>
                <div style={{ marginBottom: 6, fontSize: 14, color: "#555" }}>
                  <span style={{ fontWeight: 600 }}>Impact:</span>{" "}
                  <span
                    style={{
                      fontWeight: 700,
                      color:
                        impactCategory === "Critical"
                          ? "#c0392b"
                          : impactCategory === "High"
                          ? "#e74c3c"
                          : impactCategory === "Moderate"
                          ? "#f39c12"
                          : impactCategory === "Low"
                          ? "#27ae60"
                          : "#95a5a6",
                    }}
                  >
                    {impactCategory}
                  </span>
                </div>
                {impactExplanation && (
                  <div
                    style={{
                      marginTop: 8,
                      fontSize: 13,
                      color: "#666",
                      fontStyle: "italic",
                      lineHeight: 1.5,
                    }}
                  >
                    {impactExplanation}
                  </div>
                )}
              </>
            )}
          </div>
        )}
        
        <div
          style={{
            width: "100%",
            marginBottom: 10,
            fontWeight: 500,
            color: "#222",
          }}
        >
          Please enter Wallet Passphrase to Complete Transaction
        </div>
        <input
          type="password"
          value={passphrase}
          onChange={(e) => setPassphrase(e.target.value)}
          placeholder="Wallet passphrase"
          style={{
            width: "100%",
            padding: "0.7rem 1rem",
            borderRadius: 8,
            border: "1px solid #ccc",
            fontSize: 16,
            marginBottom: 18,
            fontFamily: "Inter, Segoe UI, Arial, sans-serif",
            background: "#f8fafd",
            color: "#222",
          }}
        />
        {error && (
          <div style={{ color: "#e74c3c", fontWeight: 600, marginBottom: 10 }}>
            {error}
          </div>
        )}
        {sendResult && (
          <div
            style={{
              color: "#27ae60",
              fontWeight: 600,
              marginBottom: 10,
              whiteSpace: "pre-line",
            }}
          >
            {sendResult}
          </div>
        )}
        <div
          style={{
            display: "flex",
            width: "100%",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <button
            onClick={onClose}
            style={{
              flex: 1,
              background: "#f4f7fa",
              color: "#222",
              border: "none",
              borderRadius: 8,
              padding: "0.8rem 0",
              fontWeight: 600,
              fontSize: 16,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={sending || !passphrase}
            style={{
              flex: 1,
              background: sending ? "#aaa" : "#27ae60",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "0.8rem 0",
              fontWeight: 600,
              fontSize: 16,
              cursor: sending ? "not-allowed" : "pointer",
            }}
          >
            {" "}
            {sending ? "Sending..." : "Confirm"}{" "}
          </button>
        </div>
      </div>
    </div>
  );
}

function Typewriter({ text, color = "#222" }) {
  const [typed, setTyped] = useState("");
  const typingTimeout = useRef(null);
  useEffect(() => {
    setTyped("");
    let i = 0;
    function typeNext() {
      setTyped(text.slice(0, i));
      if (i < text.length) {
        i++;
        typingTimeout.current = setTimeout(typeNext, 18);
      }
    }
    typeNext();
    return () => clearTimeout(typingTimeout.current);
  }, [text]);
  return (
    <span style={{ color }}>
      {typed}
      {typed.length < text.length && <span style={{ color: "#aaa" }}>|</span>}
    </span>
  );
}

export default function App() {
  const [address, setAddress] = useState("");
  const [pubKey, setPubKey] = useState("");
  const [balance, setBalance] = useState("");
  const [network, setNetwork] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toAddress, setToAddress] = useState("");
  const [showPubKey, setShowPubKey] = useState(false);
  const [amount, setAmount] = useState("");
  const [verdict, setVerdict] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [typedVerdict, setTypedVerdict] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [sending, setSending] = useState("");
  const [sendResult, setSendResult] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [modalVerdict, setModalVerdict] = useState("");
  const [modalDetails, setModalDetails] = useState("");
  const [riskScore, setRiskScore] = useState(null);
  const [addressType, setAddressType] = useState(null);
  const [impactCategory, setImpactCategory] = useState(null);
  const [impactExplanation, setImpactExplanation] = useState("");
  const typingTimeout = useRef(null);

  // Helper to mask the public key
  function getMaskedPubKey(pubKey) {
    if (!pubKey) return "";
    if (showPubKey) return pubKey;
    if (pubKey.length <= 8) return pubKey;
    return pubKey.slice(0, 4) + "••••••••" + pubKey.slice(-4);
  }

  // Typing animation effect for verdict
  useEffect(() => {
    if (!verdict) {
      setTypedVerdict("");
      return;
    }
    setTypedVerdict("");
    let i = 0;
    function typeNext() {
      setTypedVerdict((prev) => verdict.slice(0, i));
      if (i < verdict.length) {
        i++;
        typingTimeout.current = setTimeout(typeNext, 18); // typing speed (ms)
      }
    }
    typeNext();
    return () => clearTimeout(typingTimeout.current);
  }, [verdict]);

  useEffect(() => {
    async function fetchWallet() {
      setLoading(true);
      setError("");
      try {
        const walletRes = await fetch("http://127.0.0.1:5001/api/wallet");
        const walletData = await walletRes.json();
        setAddress(walletData.address);
        setPubKey(walletData.pub_key);

        const balanceRes = await fetch("http://127.0.0.1:5001/api/balance");
        const balanceData = await balanceRes.json();
        // Extract only the numeric value and token from the returned string
        // Example: "Balance on address 0x... is: 0ETH"
        let balanceStr = balanceData.balance;
        let balanceValue = balanceStr;
        let match = balanceStr.match(/is: ([^\s]+)([A-Z]*)/);
        if (match) {
          balanceValue = match[1] + (match[2] ? " " + match[2] : "");
        }
        setBalance(balanceValue);

        const networkRes = await fetch("http://127.0.0.1:5001/api/network");
        const networkData = await networkRes.json();
        setNetwork(networkData.network);
      } catch (err) {
        setError("Failed to fetch wallet info.");
      }
      setLoading(false);
    }
    fetchWallet();
  }, []);

  async function handleVerifyAndOpenModal(e) {
    e.preventDefault();
    setVerifying(true);
    setVerdict("");
    setError("");
    setSendResult("");
    setModalVerdict("");
    setModalDetails("");
    setRiskScore(null);
    setAddressType(null);
    setImpactCategory(null);
    setImpactExplanation("");
    setSending(false);
    setPassphrase("");
    try {
      const res = await fetch("http://127.0.0.1:5001/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          address: toAddress,
          amount: amount,           // Transaction amount for impact calculation
          sender_address: pubKey    // Sender's address for relative financial impact
        }),
      });
      const data = await res.json();
      if (data.result) {
        // Check if high risk using new OpenAI format
        const resultText = data.result;

        const isHighRisk =
          resultText.toLowerCase().includes("high risk") ||
          resultText.includes("⚠️");

        setModalVerdict(resultText);
        setModalDetails(isHighRisk ? resultText : "");
        
        // Extract risk score from risk_assessment
        if (data.risk_assessment) {
          const riskScoreValue = (data.risk_assessment.risk_score * 100).toFixed(1);
          setRiskScore(riskScoreValue);
        }
        
        // Extract address type
        if (data.address_type) {
          setAddressType(data.address_type);
        }
        
        // Extract impact assessment if available
        if (data.impact_assessment) {
          setImpactCategory(data.impact_assessment.impact_category);
          setImpactExplanation(data.impact_assessment.explanation);
        }

        setModalOpen(true);
      } else if (data.error) {
        setError(data.error);
      } else {
        setError("Unknown error during verification.");
      }
    } catch (err) {
      setError("Failed to verify address.");
    }
    setVerifying(false);
  }

  async function handleSendTransaction() {
    setSendResult("");
    setError("");
    setSending(true);
    try {
      const res = await fetch("http://127.0.0.1:5001/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_address: toAddress,
          amount: amount,
          passphrase: passphrase,
        }),
      });
      const data = await res.json();
      if (data.result) {
        setSendResult(data.result);
      } else if (data.error) {
        setError(data.error);
      } else {
        setError("Unknown error during send.");
      }
    } catch (err) {
      setError("Failed to send transaction.");
    }
    setSending(false);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        minWidth: "100vw",
        width: "100vw",
        height: "100vh",
        background: "#0a2342",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, Segoe UI, Arial, sans-serif",
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "18px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
          padding: "2.5rem 2rem",
          minWidth: 700,
          minHeight: 340,
          display: "flex",
          flexDirection: "row",
          gap: "2.5rem",
          fontFamily: "Inter, Segoe UI, Arial, sans-serif",
          margin: "auto",
        }}
      >
        {/* Left: Wallet Info */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            fontFamily: "Inter, Segoe UI, Arial, sans-serif",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1.5rem",
              width: "100%",
            }}
          >
            <img
              src="/logo.png"
              alt="Ethereum Logo"
              style={{ width: 42, height: 42, marginRight: 16 }} // 30% larger than before
            />
            <span
              style={{
                color: "#0a2342",
                fontWeight: 700,
                fontSize: 28,
                fontFamily: "Inter, Segoe UI, Arial, sans-serif",
                textAlign: "center",
                width: "100%",
              }}
            >
              My Wallet
            </span>
          </div>
          {loading ? (
            <div>Loading...</div>
          ) : error ? (
            <div style={{ color: "#e74c3c" }}>{error}</div>
          ) : (
            <>
              <div style={{ marginBottom: "1rem" }}>
                <strong>Address:</strong>
                <div
                  style={{
                    wordBreak: "break-all",
                    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
                    color: "#555",
                    marginTop: "0.3rem",
                  }}
                >
                  {address}
                </div>
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <strong>Private Key:</strong>
                <div
                  style={{
                    wordBreak: "break-all",
                    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
                    color: "#555",
                    marginTop: "0.3rem",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {getMaskedPubKey(pubKey)}
                  <button
                    onClick={() => setShowPubKey((v) => !v)}
                    style={{
                      marginLeft: 8,
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      outline: "none",
                    }}
                    title={showPubKey ? "Hide" : "Show"}
                  >
                    {showPubKey ? (
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 20 20"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M2 10C2 10 5.5 4 10 4C14.5 4 18 10 18 10C18 10 14.5 16 10 16C5.5 16 2 10 2 10Z"
                          stroke="#0a2342"
                          strokeWidth="2"
                        />
                        <circle
                          cx="10"
                          cy="10"
                          r="3"
                          stroke="#0a2342"
                          strokeWidth="2"
                        />
                      </svg>
                    ) : (
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 20 20"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M2 10C2 10 5.5 4 10 4C14.5 4 18 10 18 10C18 10 14.5 16 10 16C5.5 16 2 10 2 10Z"
                          stroke="#0a2342"
                          strokeWidth="2"
                        />
                        <path d="M4 4L16 16" stroke="#0a2342" strokeWidth="2" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <strong>Balance:</strong>
                <div
                  style={{
                    fontSize: 24,
                    color: "#27ae60",
                    marginTop: "0.3rem",
                    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
                    fontWeight: 600,
                  }}
                >
                  {balance}
                </div>
              </div>
              <div>
                <strong>Network:</strong>
                <div
                  style={{
                    color: "#2980b9",
                    marginTop: "0.3rem",
                    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
                  }}
                >
                  {network}
                </div>
              </div>
            </>
          )}
        </div>
        {/* Right: Send ETH */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            borderLeft: "1px solid #e6e6e6",
            paddingLeft: "2rem",
            fontFamily: "Inter, Segoe UI, Arial, sans-serif",
          }}
        >
          <h3
            style={{
              color: "#0a2342",
              marginBottom: "1.2rem",
              fontSize: "1.5rem",
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
              textAlign: "center",
            }}
          >
            Send ETH
          </h3>
          <label
            htmlFor="toAddress"
            style={{
              fontWeight: 600,
              marginBottom: 8,
              color: "#222",
              display: "block",
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
            }}
          >
            To (address):
          </label>
          <input
            id="toAddress"
            type="text"
            value={toAddress}
            onChange={(e) => setToAddress(e.target.value)}
            placeholder="0x..."
            style={{
              padding: "0.7rem 1rem",
              borderRadius: 8,
              border: "1px solid #ccc",
              fontSize: 16,
              marginBottom: 20,
              marginTop: 4,
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
              background: "#f8fafd",
              color: "#222",
            }}
          />
          <label
            htmlFor="amount"
            style={{
              fontWeight: 600,
              marginBottom: 8,
              color: "#222",
              display: "block",
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
            }}
          >
            Amount (ETH):
          </label>
          <input
            id="amount"
            type="number"
            min="0"
            step="any"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            style={{
              padding: "0.7rem 1rem",
              borderRadius: 8,
              border: "1px solid #ccc",
              fontSize: 16,
              marginBottom: 24,
              marginTop: 4,
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
              background: "#f8fafd",
              color: "#222",
            }}
          />
          <button
            style={{
              background: verifying ? "#aaa" : "#0a2342",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "0.8rem 2.2rem",
              fontSize: 18,
              fontWeight: 600,
              cursor: verifying ? "not-allowed" : "pointer",
              fontFamily: "Inter, Segoe UI, Arial, sans-serif",
              transition: "background 0.2s",
              marginTop: 8,
              boxShadow: "0 2px 8px rgba(10,35,66,0.08)",
            }}
            onClick={handleVerifyAndOpenModal}
            disabled={verifying || !toAddress || !amount}
          >
            {verifying ? "Verifying..." : "Send"}
          </button>
          {sendResult && (
            <div
              style={{
                marginTop: 18,
                color: "#27ae60",
                fontWeight: 600,
                whiteSpace: "pre-line",
                background: "#f4f7fa",
                borderRadius: 10,
                padding: "1.1rem 1.3rem",
                fontSize: 16,
                fontFamily: "Menlo, Monaco, 'Fira Mono', monospace",
                boxShadow: "0 2px 8px rgba(10,35,66,0.04)",
                minHeight: 60,
                transition: "background 0.2s",
              }}
            >
              {sendResult}
            </div>
          )}
          {typedVerdict && (
            <div
              style={{
                marginTop: 18,
                fontWeight: 600,
                color: typedVerdict.startsWith("SuspETHious: Transacting with")
                  ? "#e74c3c"
                  : typedVerdict.trim() === "SuspETHious: Recipient Verified"
                  ? "#27ae60"
                  : "#222",
                whiteSpace: "pre-line",
                background: "#f4f7fa",
                borderRadius: 10,
                padding: "1.1rem 1.3rem",
                fontSize: 16,
                fontFamily: "Menlo, Monaco, 'Fira Mono', monospace",
                boxShadow: "0 2px 8px rgba(10,35,66,0.04)",
                minHeight: 60,
                transition: "background 0.2s",
              }}
            >
              {typedVerdict}
              {typedVerdict.length < verdict.length && (
                <span style={{ color: "#aaa" }}>|</span>
              )}
            </div>
          )}
          {error && (
            <div
              style={{
                marginTop: 18,
                color: "#e74c3c",
                fontWeight: 600,
              }}
            >
              {error}
            </div>
          )}
        </div>
      </div>
      <Modal
        open={modalOpen}
        verdict={modalVerdict}
        details={modalDetails}
        riskScore={riskScore}
        addressType={addressType}
        impactCategory={impactCategory}
        impactExplanation={impactExplanation}
        onClose={() => {
          setModalOpen(false);
          setPassphrase("");
          setSendResult("");
          setError("");
        }}
        onConfirm={handleSendTransaction}
        sending={sending}
        sendResult={sendResult}
        error={error}
        passphrase={passphrase}
        setPassphrase={setPassphrase}
      />
    </div>
  );
}
