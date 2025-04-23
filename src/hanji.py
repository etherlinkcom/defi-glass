import requests
from datetime import datetime
import psycopg2
import os
from web3 import Web3

# Dictionary of orderbook addresses
orderbooks = {
    "wxtz-usdc": "0xD0BC067CF877F7b76CeB331891331d9e6ACda1a7",
    "weth-usdc": "0x65eA4dD7f789C71C0f57Ed84b3BDC3062898D3CB",
    "wbtc-usdc": "0xbB6B01D94E3f6Ebae8647cB56D544f57928aB758",
}

NODE_URL = "https://node.mainnet.etherlink.com" # TODO: move to env vars

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

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

w3 = Web3(Web3.HTTPProvider(NODE_URL))

def hanji_get_total_tvl():
    """Writes orderbook TVL data to the SQL database."""
    
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

    for orderbook_name in orderbooks:
        market_identifier = orderbooks[orderbook_name]
        
        try:
            market_params = {"market": market_identifier}
            market_response = requests.get("https://api.hanji.io/markets", params=market_params)
            market_response.raise_for_status()
            market_data = market_response.json()[0]

            base_token_address = market_data['baseToken']['contractAddress']
            base_token_symbol = market_data["baseToken"]["symbol"]
            quote_token_address = market_data["quoteToken"]["contractAddress"]
            quote_token_symbol = market_data["quoteToken"]["symbol"]

            baseTokenContract = w3.eth.contract(
                address=Web3.to_checksum_address(base_token_address), abi=TOKEN_ABI
            )

            quoteTokenContract = w3.eth.contract(
                address=Web3.to_checksum_address(quote_token_address), abi=TOKEN_ABI
            )

            baseTokenBalance = baseTokenContract.functions.balanceOf(
                Web3.to_checksum_address(market_identifier)
            ).call() / (10 ** market_data["baseToken"]["decimals"])

            quoteTokenBalance = quoteTokenContract.functions.balanceOf(
                Web3.to_checksum_address(market_identifier)
            ).call() / (10 ** market_data["quoteToken"]["decimals"])

            cursor.execute(
                """INSERT INTO tvl_history (protocol, type, token, amount, timestamp, address)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('hanji', orderbook_name, base_token_symbol, float(baseTokenBalance), current_timestamp, base_token_address)
            )

            cursor.execute(
                """INSERT INTO tvl_history (protocol, type, token, amount, timestamp, address)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('hanji', orderbook_name, quote_token_symbol, float(quoteTokenBalance), current_timestamp, quote_token_address)
            )

        except Exception as e:
            print(f"Error processing {orderbook_name}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cursor.close()
    conn.close()
    print("Data successfully written to the database.")
