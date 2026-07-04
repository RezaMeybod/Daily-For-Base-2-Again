#!/usr/bin/env python3
"""
deploy_base_token.py

Deploy a minimal ERC‑20 token (named “Base Token”) to an EVM‑compatible chain
(e.g. Base, Ethereum, Sepolia) with web3.py.

Requirements
------------
- Python 3.9+
- pip install web3 eth-account
- RPC endpoint (Base RPC, Alchemy, Infura, etc.)
- Deployer private key (never commit it)

Usage
-----
$ python deploy_base_token.py \
    --rpc https://base-mainnet.g.alchemy.com/v2/<API_KEY> \
    --private-key 0xYOUR_PRIVATE_KEY \
    --name "Base Token" \
    --symbol "BASE" \
    --decimals 18 \
    --total-supply 1000000
"""

import argparse
import json
import sys
from web3 import Web3
from eth_account import Account
from web3.exceptions import ContractLogicError

# --------------------------------------------------------------------------- #
# ERC‑20 ABI & bytecode (compiled with Solidity 0.8.24)
# --------------------------------------------------------------------------- #
BASE_TOKEN_ABI = json.loads(
    """
[
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"},{"internalType":"uint8","name":"_decimals","type":"uint8"},{"internalType":"uint256","name":"_initialSupply","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[{"internalType":"address","name":"_to","type":"address"},{"internalType":"uint256","name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"_spender","type":"address"},{"internalType":"uint256","name":"_value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"_from","type":"address"},{"internalType":"address","name":"_to","type":"address"},{"internalType":"uint256","name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}
]
"""
)

# Truncated for brevity – replace with the full compiled bytecode of the contract
BASE_TOKEN_BYTECODE = (
    "608060405234801561001057600080fd5b506040516104b93803806104b983398101604081"
    "5281016040805180910390f35b600080fd5b600080fd5b600080fd5b6000908152602080fd"
    "6000819055507f5a0e1f1e2d2e3f5c4d6a5a5c5b6c4b7d8e9f5a6b7c8d9e0f1a2b3c4d5e6f7"
    "8a5b6c7d8e9f5a6b7c8d9e0f1a2b3c4d5e6000604051808303818602009a603f565b6000"
    "fd5b6100b58061006c6000396000f3fe608060405260043610610056576000357c01"
    # ... (full bytecode goes here) ...
    "0015f0b3f5e2c5f0b3a0d1c3f7e6d7c9b8a6c5d4e3f2c1b0a9e8d7c6b5a4f3e2d1c0b"
)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deploy a simple ERC‑20 Base Token")
    p.add_argument("--rpc", required=True, help="EVM RPC endpoint URL")
    p.add_argument("--private-key", required=True, help="Deployer private key")
    p.add_argument("--name", default="Base Token", help="Token name")
    p.add_argument("--symbol", default="BASE", help="Token symbol")
    p.add_argument("--decimals", type=int, default=18, help="Decimals (default 18)")
    p.add_argument(
        "--total-supply",
        type=float,
        required=True,
        help="Total supply in human‑readable units (e.g. 1_000_000)",
    )
    p.add_argument("--gas-price", type=int, default=None, help="Gas price in wei")
    p.add_argument("--nonce", type=int, default=None, help="Tx nonce (optional)")
    return p.parse_args()

def load_account(pk: str) -> Account:
    pk = pk.strip()
    if pk.startswith("0x"):
        pk = pk[2:]
    return Account.from_key(pk)

def build_constructor_args(name: str, symbol: str, decimals: int, total_supply: float):
    supply_int = int(total_supply * (10 ** decimals))
    return (name, symbol, decimals, supply_int)

def main() -> None:
    args = parse_args()
    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        sys.exit("❌ Cannot connect to the RPC endpoint")
    acct = load_account(args.private_key)
    print(f"🔑 Deployer address: {acct.address}")

    contract = w3.eth.contract(abi=BASE_TOKEN_ABI, bytecode=BASE_TOKEN_BYTECODE)

    ctor_args = build_constructor_args(
        args.name, args.symbol, args.decimals, args.total_supply
    )

    # Estimate gas
    try:
        gas_est = contract.constructor(*ctor_args).estimate_gas({"from": acct.address})
    except ContractLogicError as e:
        sys.exit(f"❌ Gas estimation failed: {e}")

    tx_dict = contract.constructor(*ctor_args).build_transaction(
        {
            "from": acct.address,
            "nonce": args.nonce if args.nonce is not None else w3.eth.get_transaction_count(acct.address),
            "gas": gas_est + 10_000,
            "gasPrice": args.gas_price if args.gas_price is not None else w3.eth.gas_price,
        }
    )

    signed = acct.sign_transaction(tx_dict)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"📤 Tx sent – hash: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"✅ Deployed at: {receipt.contractAddress}")
    else:
        print("❌ Deployment failed (receipt status = 0)")

if __name__ == "__main__":
    main()
