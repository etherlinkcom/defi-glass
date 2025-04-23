import os
import requests
from datetime import datetime
from web3 import Web3

IMC_WALLET = "0xf99fdd1e71838433516de7ad98aa82bfa3f17ae2"
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/id/QmXwNKGXt5EATr4mudWxuAZ6kLgiEnXcZv99dtmmHMTGeP"

w3 = Web3(Web3.HTTPProvider(os.getenv("ETHERLINK_NODE_URL")))

TOKEN_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

slTOKENS = {
    "usdc": {"address": "0xd03bfdf9b26db1e6764724d914d7c3d18106a9fb", "decimals": 6},
    "wxtz": {"address": "0x008ae222661b6a42e3a097bd7aac15412829106b", "decimals": 18},
    "weth": {"address": "0x301bea8b7c0ef6722c937c07da4d53931f61969c", "decimals": 18},
    "usdt": {"address": "0x998098a1b2e95e2b8f15360676428edfd976861f", "decimals": 6},
    "wbtc": {"address": "0xfca0802cb10b3b134a91e07f03965f63ef4b23ea", "decimals": 8},
    "mtbill": {"address": "0x187b7b83e8cab442ad0bfeae38067f3eb38a2d72", "decimals": 18},
    "mbasis": {"address": "0x660adef5993167acdb490df287f4db6cc226ffeb", "decimals": 18},
}

def get_balance_of(token_address, user_address):
    """Fetches token balance of a given user."""
    token_contract = w3.eth.contract(
        address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI
    )
    balance = token_contract.functions.balanceOf(
        Web3.to_checksum_address(user_address)
    ).call()
    return balance

def fetch_reserve_data(token_address):
    """Fetches totalCurrentVariableDebt and totalLiquidity for a Superlend reserve."""
    query = f"""{{
      reserves(where: {{aToken_: {{id: "{token_address}"}}}}) {{
        totalCurrentVariableDebt
        totalLiquidity
      }}
    }}"""
    response = requests.post(SUBGRAPH_URL, json={"query": query})
    if not response.ok or not response.json().get("data", {}).get("reserves"):
        print("No data found")
        return 0, 0

    reserve_data = response.json()["data"]["reserves"][0]
    decimals = slTOKENS[next(k for k, v in slTOKENS.items() if v["address"] == token_address)]["decimals"]
    total_current_variable_debt = float(reserve_data["totalCurrentVariableDebt"]) / (10 ** decimals)
    total_liquidity = float(reserve_data["totalLiquidity"]) / (10 ** decimals)
    return total_current_variable_debt, total_liquidity

def superlend_get_total_tvl(cursor):
    """Writes TVL data to the SQL database using a provided cursor."""
    current_timestamp = datetime.utcnow().isoformat()

    for token_name in slTOKENS:
        token_address = slTOKENS[token_name]["address"]
        
        try:
            token_contract = w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI
            )
            total_supply = token_contract.functions.totalSupply().call()
            imc_balance = get_balance_of(token_address, IMC_WALLET)
            total_current_variable_debt, total_liquidity = fetch_reserve_data(token_address)

            cursor.execute(
                """INSERT INTO tvl_history (protocol, type, token, amount, timestamp, address)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ("superlend", token_name, token_name, float(total_liquidity), current_timestamp, token_address)
            )

        except Exception as e:
            print(f"Error processing {token_name}: {e}")
            raise
