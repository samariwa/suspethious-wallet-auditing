"""
Blacklist Database Update Script
=================================
This script checks external sources for new malicious addresses and updates
the local blacklist database.

Currently monitors:
- ScamSniffer database (GitHub)
- Forta Network malicious labels (GitHub)

Usage:
    python update_blacklist.py
    
The script will:
1. Load current blacklist_database.json
2. Fetch latest data from ScamSniffer
3. Fetch latest data from Forta Network
4. Identify new addresses not in current database
5. Update blacklist_database.json with new addresses
6. Generate update report
"""

import json
import requests
import pandas as pd
from datetime import datetime
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================
BLACKLIST_PATH = "blacklist_database.json"
BACKUP_PATH = f"blacklist_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# External sources
SCAMSNIFFER_URL = "https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json"
FORTA_ETHERSCAN_URL = "https://raw.githubusercontent.com/forta-network/labelled-datasets/main/labels/1/etherscan_malicious_labels.csv"
FORTA_CONTRACTS_URL = "https://raw.githubusercontent.com/forta-network/labelled-datasets/main/labels/1/malicious_smart_contracts.csv"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_current_blacklist():
    """Load current blacklist database"""
    try:
        with open(BLACKLIST_PATH, 'r') as f:
            blacklist = json.load(f)
        return set(addr.lower() for addr in blacklist)
    except FileNotFoundError:
        print(f"⚠ Warning: {BLACKLIST_PATH} not found. Starting with empty blacklist.")
        return set()
    except Exception as e:
        print(f"✗ Error loading blacklist: {e}")
        sys.exit(1)


def backup_current_blacklist(current_blacklist):
    """Create backup of current blacklist"""
    try:
        blacklist_list = sorted(list(current_blacklist))
        with open(BACKUP_PATH, 'w') as f:
            json.dump(blacklist_list, f, indent=2)
        print(f"  ✓ Backup created: {BACKUP_PATH}")
        return True
    except Exception as e:
        print(f"  ✗ Error creating backup: {e}")
        return False


def fetch_scamsniffer():
    """Fetch latest addresses from ScamSniffer"""
    print("\n[Checking ScamSniffer Database]")
    try:
        response = requests.get(SCAMSNIFFER_URL, timeout=30)
        response.raise_for_status()
        scamsniffer_data = response.json()
        addresses = set(addr.lower() for addr in scamsniffer_data)
        print(f"  ✓ Fetched {len(addresses):,} addresses from ScamSniffer")
        return addresses
    except requests.RequestException as e:
        print(f"  ✗ Network error fetching ScamSniffer: {e}")
        return set()
    except json.JSONDecodeError as e:
        print(f"  ✗ Error parsing ScamSniffer JSON: {e}")
        return set()
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return set()


def fetch_forta_etherscan():
    """Fetch latest addresses from Forta Network Etherscan labels"""
    print("\n[Checking Forta Network - Etherscan Labels]")
    try:
        response = requests.get(FORTA_ETHERSCAN_URL, timeout=30)
        response.raise_for_status()
        forta_df = pd.read_csv(pd.io.common.StringIO(response.text))
        
        if 'Address' not in forta_df.columns:
            print(f"  ✗ 'Address' column not found in Forta data")
            return set()
        
        addresses = set(forta_df['Address'].str.lower().unique())
        print(f"  ✓ Fetched {len(addresses):,} addresses from Forta Etherscan labels")
        return addresses
    except requests.RequestException as e:
        print(f"  ✗ Network error fetching Forta Etherscan: {e}")
        return set()
    except Exception as e:
        print(f"  ✗ Error processing Forta Etherscan data: {e}")
        return set()


def fetch_forta_contracts():
    """Fetch latest addresses from Forta Network malicious contracts"""
    print("\n[Checking Forta Network - Malicious Contracts]")
    try:
        response = requests.get(FORTA_CONTRACTS_URL, timeout=30)
        response.raise_for_status()
        forta_df = pd.read_csv(pd.io.common.StringIO(response.text))
        
        if 'contract_creator' not in forta_df.columns:
            print(f"  ⚠ 'contract_creator' column not found, skipping")
            return set()
        
        # Extract contract creator addresses
        addresses = set(
            forta_df['contract_creator'].dropna().str.lower().unique()
        )
        addresses = {addr for addr in addresses if addr and addr.startswith('0x')}
        print(f"  ✓ Fetched {len(addresses):,} contract creator addresses from Forta")
        return addresses
    except requests.RequestException as e:
        print(f"  ✗ Network error fetching Forta contracts: {e}")
        return set()
    except Exception as e:
        print(f"  ✗ Error processing Forta contracts data: {e}")
        return set()


def save_updated_blacklist(blacklist_set):
    """Save updated blacklist to file"""
    try:
        blacklist_list = sorted(list(blacklist_set))
        with open(BLACKLIST_PATH, 'w') as f:
            json.dump(blacklist_list, f, indent=2)
        return True
    except Exception as e:
        print(f"✗ Error saving updated blacklist: {e}")
        return False


# ============================================================================
# UPDATE REPORT
# ============================================================================

def generate_report(current_count, new_addresses, source_stats):
    """Generate update report"""
    print(f"\n{'='*80}")
    print(f"BLACKLIST UPDATE REPORT")
    print(f"{'='*80}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nCurrent Database Size: {current_count:,} addresses")
    print(f"New Addresses Found: {len(new_addresses):,} addresses")
    print(f"Updated Database Size: {current_count + len(new_addresses):,} addresses")
    
    print(f"\n{'-'*80}")
    print(f"SOURCE BREAKDOWN")
    print(f"{'-'*80}")
    for source, stats in source_stats.items():
        print(f"\n{source}:")
        print(f"  Total addresses: {stats['total']:,}")
        print(f"  New addresses: {stats['new']:,}")
        print(f"  Already in database: {stats['existing']:,}")
    
    if new_addresses:
        print(f"\n{'-'*80}")
        print(f"SAMPLE OF NEW ADDRESSES (first 10)")
        print(f"{'-'*80}")
        for addr in sorted(list(new_addresses))[:10]:
            print(f"  {addr}")
        if len(new_addresses) > 10:
            print(f"  ... and {len(new_addresses) - 10} more")
    
    print(f"\n{'='*80}")


def save_report(current_count, new_addresses, source_stats):
    """Save update report to file"""
    report_path = f"blacklist_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("BLACKLIST UPDATE REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nCurrent Database Size: {current_count:,} addresses\n")
            f.write(f"New Addresses Found: {len(new_addresses):,} addresses\n")
            f.write(f"Updated Database Size: {current_count + len(new_addresses):,} addresses\n")
            
            f.write(f"\n{'-'*80}\n")
            f.write(f"SOURCE BREAKDOWN\n")
            f.write(f"{'-'*80}\n")
            for source, stats in source_stats.items():
                f.write(f"\n{source}:\n")
                f.write(f"  Total addresses: {stats['total']:,}\n")
                f.write(f"  New addresses: {stats['new']:,}\n")
                f.write(f"  Already in database: {stats['existing']:,}\n")
            
            if new_addresses:
                f.write(f"\n{'-'*80}\n")
                f.write(f"NEW ADDRESSES\n")
                f.write(f"{'-'*80}\n")
                for addr in sorted(list(new_addresses)):
                    f.write(f"{addr}\n")
            
            f.write(f"\n{'='*80}\n")
        
        print(f"\n✓ Report saved to: {report_path}")
    except Exception as e:
        print(f"\n✗ Error saving report: {e}")


# ============================================================================
# MAIN UPDATE PROCESS
# ============================================================================

def main():
    print(f"\n{'='*80}")
    print(f"BLACKLIST DATABASE UPDATE")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load current blacklist
    print("[Step 1/5] Loading Current Blacklist Database")
    current_blacklist = load_current_blacklist()
    print(f"  ✓ Loaded {len(current_blacklist):,} addresses from current database")
    
    # Create backup
    print("\n[Step 2/5] Creating Backup")
    if not backup_current_blacklist(current_blacklist):
        print("\n⚠ Warning: Could not create backup. Continue? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("Update cancelled.")
            sys.exit(0)
    
    # Fetch from external sources
    print("\n[Step 3/5] Fetching Latest Data from External Sources")
    
    scamsniffer_addresses = fetch_scamsniffer()
    forta_etherscan_addresses = fetch_forta_etherscan()
    forta_contracts_addresses = fetch_forta_contracts()
    
    # Identify new addresses
    print("\n[Step 4/5] Identifying New Addresses")
    
    all_new_addresses = set()
    source_stats = {}
    
    # ScamSniffer
    scamsniffer_new = scamsniffer_addresses - current_blacklist
    all_new_addresses.update(scamsniffer_new)
    source_stats['ScamSniffer'] = {
        'total': len(scamsniffer_addresses),
        'new': len(scamsniffer_new),
        'existing': len(scamsniffer_addresses) - len(scamsniffer_new)
    }
    print(f"  • ScamSniffer: {len(scamsniffer_new):,} new addresses")
    
    # Forta Etherscan
    forta_etherscan_new = forta_etherscan_addresses - current_blacklist
    all_new_addresses.update(forta_etherscan_new)
    source_stats['Forta Etherscan Labels'] = {
        'total': len(forta_etherscan_addresses),
        'new': len(forta_etherscan_new),
        'existing': len(forta_etherscan_addresses) - len(forta_etherscan_new)
    }
    print(f"  • Forta Etherscan: {len(forta_etherscan_new):,} new addresses")
    
    # Forta Contracts
    forta_contracts_new = forta_contracts_addresses - current_blacklist
    all_new_addresses.update(forta_contracts_new)
    source_stats['Forta Malicious Contracts'] = {
        'total': len(forta_contracts_addresses),
        'new': len(forta_contracts_new),
        'existing': len(forta_contracts_addresses) - len(forta_contracts_new)
    }
    print(f"  • Forta Contracts: {len(forta_contracts_new):,} new addresses")
    
    print(f"\n  ✓ Total new addresses found: {len(all_new_addresses):,}")
    
    # Update blacklist if new addresses found
    if all_new_addresses:
        print("\n[Step 5/5] Updating Blacklist Database")
        updated_blacklist = current_blacklist.union(all_new_addresses)
        
        if save_updated_blacklist(updated_blacklist):
            print(f"  ✓ Blacklist updated successfully")
            print(f"  ✓ New size: {len(updated_blacklist):,} addresses")
            
            # Generate and save report
            generate_report(len(current_blacklist), all_new_addresses, source_stats)
            save_report(len(current_blacklist), all_new_addresses, source_stats)
        else:
            print(f"  ✗ Failed to save updated blacklist")
            print(f"  ℹ Backup available at: {BACKUP_PATH}")
            sys.exit(1)
    else:
        print("\n[Step 5/5] No Update Needed")
        print(f"  ℹ No new addresses found. Database is up to date.")
        
        # Generate report anyway
        generate_report(len(current_blacklist), all_new_addresses, source_stats)
    
    print(f"\n{'='*80}")
    print(f"UPDATE COMPLETE")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
