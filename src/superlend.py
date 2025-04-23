import requests
from datetime import datetime
import psycopg2
import os
from web3 import Web3

NODE_URL = "https://node.mainnet.etherlink.com"

IMC_WALLET = "0xf99fdd1e71838433516de7ad98aa82bfa3f17ae2"

SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/id/QmXwNKGXt5EATr4mudWxuAZ6kLgiEnXcZv99dtmmHMTGeP"

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

# slTokens decimals
tokenDecimals = {
    "0xd03bfdf9b26db1e6764724d914d7c3d18106a9fb": 6,
    "0x008ae222661b6a42e3a097bd7aac15412829106b": 18,
    "0x301bea8b7c0ef6722c937c07da4d53931f61969c": 18,
    "0x998098a1b2e95e2b8f15360676428edfd976861f": 6,
    "0xfca0802cb10b3b134a91e07f03965f63ef4b23ea": 8,
    "0x187b7b83e8cab442ad0bfeae38067f3eb38a2d72": 18,
    "0x660adef5993167acdb490df287f4db6cc226ffeb": 18,
}

# addresses of slTokens
slTOKENS = {
    "usdc": {"address": "0xd03bfdf9b26db1e6764724d914d7c3d18106a9fb", "decimals": 6},
    "wxtz": {"address": "0x008ae222661b6a42e3a097bd7aac15412829106b", "decimals": 18},
    "weth": {"address": "0x301bea8b7c0ef6722c937c07da4d53931f61969c", "decimals": 18},
    "usdt": {"address": "0x998098a1b2e95e2b8f15360676428edfd976861f", "decimals": 6},
    "wbtc": {"address": "0xfca0802cb10b3b134a91e07f03965f63ef4b23ea", "decimals": 8},
    "mtbill": {"address": "0x187b7b83e8cab442ad0bfeae38067f3eb38a2d72", "decimals": 18},
    "mbasis": {"address": "0x660adef5993167acdb490df287f4db6cc226ffeb", "decimals": 18},
}

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

w3 = Web3(Web3.HTTPProvider(NODE_URL))

def get_balanceOf(aToken_address, user_address):
    """Fetches slToken balance of a given user"""

    w3 = Web3(Web3.HTTPProvider(NODE_URL))

    tokenContract = w3.eth.contract(
        address=Web3.to_checksum_address(aToken_address), abi=TOKEN_ABI
    )

    balance = tokenContract.functions.balanceOf(
        Web3.to_checksum_address(user_address)
    ).call()

    return balance

def fetch_reserve_data(aToken_address):
    """Fetches current totalCurrentVariableDebt and totalLiquidity for a given Superlend reserve"""

    all_items = []

    query = f"""{{
      reserves(where: {{aToken_: {{id: "{aToken_address}"}}}}) {{
        totalCurrentVariableDebt
        totalLiquidity
      }}
    }}"""

    response = requests.post(SUBGRAPH_URL, json={"query": query})
    if not response.ok or not response.json().get("data", {}).get("reserves"):
        print("No data found")
        return all_items

    reserve_data = response.json()["data"]["reserves"][0]

    totalCurrentVariableDebt = float(reserve_data.get("totalCurrentVariableDebt")) / (
        10 ** tokenDecimals[aToken_address]
    )
    totalLiquidity = float(reserve_data.get("totalLiquidity")) / (
        10 ** tokenDecimals[aToken_address]
    )

    return totalCurrentVariableDebt, totalLiquidity

def superlend_get_total_tvl():
    """Writes TVL data to the SQL database."""
    
    # Database connection parameters - replace with your actual credentials
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    current_timestamp = datetime.utcnow().isoformat()

    for slToken in slTOKENS:
        slToken_address = slTOKENS[slToken]["address"]
        
        try:
            tokenContract = w3.eth.contract(
                address=Web3.to_checksum_address(slToken_address), abi=TOKEN_ABI
            )

            slTokenTotalSupply = (
                tokenContract.functions.totalSupply().call()
            )  # / (10 ** tokenDecimals[slToken_address])
            slToken_imc_balance = get_balanceOf(
                slToken_address, IMC_WALLET
            )  # / (10 ** tokenDecimals[slToken_address])

            totalCurrentVariableDebt, totalLiquidity = fetch_reserve_data(slToken_address)

            totalLiquidity = totalLiquidity

            imcLiquidity = (slToken_imc_balance / slTokenTotalSupply) * totalLiquidity

            cursor.execute(
                """INSERT INTO tvl_history (protocol, type, token, amount, timestamp, address)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('superlend', slToken, slToken, float(totalLiquidity), current_timestamp, slToken_address)
            )

        except Exception as e:
            print(f"Error processing {slToken}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cursor.close()
    conn.close()
    print("Data successfully written to the database.")
