"""
End-to-End Latency Benchmark
=============================
Measures wallet scoring latency across 200 random addresses from the dataset.

Usage:
    python latency_benchmark.py

Requirements:
    - dataset_v2.csv must exist in Model Training/ directory
    - All trained models must be available
    - API keys configured in .env
"""

import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import wallet scoring functionality
import wallet_scoring as ws

def select_random_wallets(dataset_path, n_samples=200, random_state=42):
    """
    Select random wallet addresses from dataset.
    
    Args:
        dataset_path: Path to dataset CSV
        n_samples: Number of addresses to sample
        random_state: Random seed for reproducibility
        
    Returns:
        List of wallet addresses
    """
    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    # Clean address column name (remove leading/trailing spaces)
    df.columns = df.columns.str.strip()
    
    print(f"Dataset loaded: {len(df)} total wallets")
    print(f"Sampling {n_samples} random addresses...")
    
    # Sample addresses
    sampled = df.sample(n=n_samples, random_state=random_state)
    addresses = sampled['Address'].tolist()
    
    print(f"Selected {len(addresses)} addresses for benchmarking\n")
    return addresses


def benchmark_latency(addresses):
    """
    Measure end-to-end latency for wallet scoring.
    
    Args:
        addresses: List of wallet addresses to test
        
    Returns:
        Dictionary with latency statistics
    """
    print("="*80)
    print("LATENCY BENCHMARK - WALLET SCORING")
    print("="*80)
    print(f"Total requests: {len(addresses)}")
    print(f"Test mode: Sequential (no parallelism)")
    print("="*80)
    
    # Load models once (not counted in per-request latency)
    print("\n[Setup] Loading models and blacklist...")
    setup_start = time.time()
    models = ws.load_models()
    blacklist_set = ws.load_blacklist()
    setup_time = time.time() - setup_start
    print(f"Setup completed in {setup_time:.3f} seconds\n")
    
    print("="*80)
    print("BENCHMARKING IN PROGRESS...")
    print("="*80)
    
    latencies = []
    successful_requests = 0
    failed_requests = 0
    
    for i, address in enumerate(addresses, 1):
        try:
            # Measure end-to-end latency for single wallet scoring
            start_time = time.time()
            result = ws.score_wallet(address, models, blacklist_set)
            end_time = time.time()
            
            latency = end_time - start_time
            latencies.append(latency)
            successful_requests += 1
            
            # Print progress every 20 requests
            if i % 20 == 0:
                print(f"Progress: {i}/{len(addresses)} requests | "
                      f"Last latency: {latency:.3f}s | "
                      f"Running avg: {np.mean(latencies):.3f}s")
        
        except Exception as e:
            failed_requests += 1
            print(f"Request {i} FAILED for address {address[:10]}... | Error: {str(e)[:50]}")
            continue
    
    print("="*80)
    print("BENCHMARK COMPLETED")
    print("="*80)
    
    if not latencies:
        print("\nERROR: No successful requests completed!")
        return None
    
    # Calculate statistics
    latencies_array = np.array(latencies)
    stats = {
        'total_requests': len(addresses),
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'fastest_latency': np.min(latencies_array),
        'slowest_latency': np.max(latencies_array),
        'average_latency': np.mean(latencies_array),
        'std_deviation': np.std(latencies_array),
        'median_latency': np.median(latencies_array),
        'p95_latency': np.percentile(latencies_array, 95),
        'p99_latency': np.percentile(latencies_array, 99)
    }
    
    return stats


def print_results(stats):
    """Print formatted benchmark results."""
    if stats is None:
        return
    
    print("\n" + "="*80)
    print("LATENCY BENCHMARK RESULTS")
    print("="*80)
    
    print(f"\nRequest Summary:")
    print(f"  Total requests:      {stats['total_requests']}")
    print(f"  Successful requests: {stats['successful_requests']}")
    print(f"  Failed requests:     {stats['failed_requests']}")
    print(f"  Success rate:        {(stats['successful_requests'] / stats['total_requests']) * 100:.2f}%")
    
    print(f"\nLatency Statistics:")
    print(f"  Fastest latency:     {stats['fastest_latency']:.3f} seconds")
    print(f"  Slowest latency:     {stats['slowest_latency']:.3f} seconds")
    print(f"  Average latency:     {stats['average_latency']:.3f} seconds")
    print(f"  Standard deviation:  {stats['std_deviation']:.3f} seconds")
    print(f"  Median latency:      {stats['median_latency']:.3f} seconds")
    
    print(f"\nPercentile Analysis:")
    print(f"  95th percentile:     {stats['p95_latency']:.3f} seconds")
    print(f"  99th percentile:     {stats['p99_latency']:.3f} seconds")
    
    print("\n" + "="*80)
    print("FORMATTED OUTPUT FOR REPORTING:")
    print("="*80)
    print(f"Total requests: {stats['successful_requests']}")
    print(f"Fastest latency: {stats['fastest_latency']:.3f} seconds")
    print(f"Slowest latency: {stats['slowest_latency']:.3f} seconds")
    print(f"Average latency: {stats['average_latency']:.3f} seconds")
    print(f"Standard deviation: {stats['std_deviation']:.3f} seconds")
    print("="*80)


def main():
    """Main benchmark execution."""
    print("\n" + "="*80)
    print("WALLET SCORING END-TO-END LATENCY BENCHMARK")
    print("="*80)
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Configuration
    DATASET_PATH = "Model Training/dataset_v2.csv"
    N_SAMPLES = 200
    RANDOM_STATE = 42
    
    # Select random addresses
    try:
        addresses = select_random_wallets(DATASET_PATH, N_SAMPLES, RANDOM_STATE)
    except Exception as e:
        print(f"ERROR: Failed to load addresses from dataset: {e}")
        sys.exit(1)
    
    # Run benchmark
    overall_start = time.time()
    stats = benchmark_latency(addresses)
    overall_time = time.time() - overall_start
    
    # Print results
    print_results(stats)
    
    print(f"\nTotal benchmark duration: {overall_time:.2f} seconds")
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
