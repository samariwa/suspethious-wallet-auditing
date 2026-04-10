"""
Calculate Average Ether Sent Per Transaction
=============================================
This script calculates the average ether sent per transaction for each wallet
in the dataset, then computes the overall average across all wallets.

Formula: avg_sent = total Ether sent / Sent tnx

Usage:
    python calculate_avg_sent_txn.py
"""

import pandas as pd
import numpy as np

# Read the dataset
print("Loading dataset...")
df = pd.read_csv('Model Training/dataset_v2.csv')
print(f"Dataset loaded: {len(df)} rows\n")

# Calculate average ether sent per transaction for each wallet
# Avoid division by zero by filtering out rows where Sent tnx = 0
print("Calculating average ether sent per transaction for each wallet...")

# Filter out wallets with no sent transactions
df_with_sent = df[df['Sent tnx'] > 0].copy()
print(f"Wallets with sent transactions: {len(df_with_sent)} out of {len(df)}")

# Calculate avg_sent for each wallet
df_with_sent['avg_sent_per_txn'] = df_with_sent['total Ether sent'] / df_with_sent['Sent tnx']

# Calculate overall statistics
overall_avg = df_with_sent['avg_sent_per_txn'].mean()
overall_median = df_with_sent['avg_sent_per_txn'].median()
overall_std = df_with_sent['avg_sent_per_txn'].std()
overall_min = df_with_sent['avg_sent_per_txn'].min()
overall_max = df_with_sent['avg_sent_per_txn'].max()

# Print results
print(f"\n{'='*80}")
print(f"AVERAGE ETHER SENT PER TRANSACTION - STATISTICS")
print(f"{'='*80}")
print(f"\nOverall Average (Mean):  {overall_avg:.6f} ETH")
print(f"Median:                  {overall_median:.6f} ETH")
print(f"Standard Deviation:      {overall_std:.6f} ETH")
print(f"Minimum:                 {overall_min:.6f} ETH")
print(f"Maximum:                 {overall_max:.6f} ETH")
print(f"\nTotal wallets analyzed:  {len(df_with_sent)}")
print(f"Wallets excluded (0 sent txn): {len(df) - len(df_with_sent)}")

# Additional breakdown by FLAG (fraud vs legitimate)
print(f"\n{'-'*80}")
print(f"BREAKDOWN BY WALLET TYPE")
print(f"{'-'*80}")

for flag in sorted(df_with_sent['FLAG'].unique()):
    flag_data = df_with_sent[df_with_sent['FLAG'] == flag]
    flag_avg = flag_data['avg_sent_per_txn'].mean()
    flag_count = len(flag_data)
    wallet_type = "FRAUD" if flag == 1 else "LEGITIMATE"
    print(f"\n{wallet_type} wallets (FLAG={flag}):")
    print(f"  Count: {flag_count}")
    print(f"  Average ether per txn: {flag_avg:.6f} ETH")

# Show some examples
print(f"\n{'-'*80}")
print(f"SAMPLE DATA (First 10 wallets with sent transactions)")
print(f"{'-'*80}")
print(df_with_sent[['Address', 'Sent tnx', 'total Ether sent', 'avg_sent_per_txn', 'FLAG']].head(10).to_string(index=False))

print(f"\n{'='*80}")
print(f"Analysis complete!")
print(f"{'='*80}\n")
