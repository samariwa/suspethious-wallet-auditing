import React, { useEffect, useState } from "react";

export default function WalletDashboard() {
  const [address, setAddress] = useState("");
  const [balance, setBalance] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchWallet() {
      setLoading(true);
      setError("");
      try {
        const walletRes = await fetch("/api/wallet");
        const walletData = await walletRes.json();
        setAddress(walletData.address);

        const balanceRes = await fetch("/api/balance");
        const balanceData = await balanceRes.json();
        setBalance(balanceData.balance);
      } catch (err) {
        setError("Failed to fetch wallet info.");
      }
      setLoading(false);
    }
    fetchWallet();
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#f5f6fa",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "12px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
          padding: "2rem 3rem",
          minWidth: "350px",
        }}
      >
        <h2 style={{ marginBottom: "1.5rem", color: "#222" }}>
          My Ethereum Wallet
        </h2>
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
                  fontFamily: "monospace",
                  color: "#555",
                  marginTop: "0.3rem",
                }}
              >
                {address}
              </div>
            </div>
            <div>
              <strong>Balance:</strong>
              <div
                style={{
                  fontSize: "1.5rem",
                  color: "#27ae60",
                  marginTop: "0.3rem",
                }}
              >
                {balance}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
