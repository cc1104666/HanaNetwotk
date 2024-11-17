import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
import aiohttp
import argparse
from web3 import Web3
from web3.exceptions import TransactionNotFound
from colorama import init, Fore, Style
import itertools
from urllib.parse import urlparse
from aiohttp_socks import ProxyType, ProxyConnector
init(autoreset=True)


RPC_URL = "https://mainnet.base.org"
CONTRACT_ADDRESS = "0xC5bf05cD32a14BFfb705Fb37a9d218895187376c"
api_url = "https://hanafuda-backend-app-520478841386.us-central1.run.app/graphql"
AMOUNT_ETH = 0.0000000001
FIREBASE_API_KEY = "AIzaSyDipzN0VRfTPnMGhQ5PSzO27Cxm3DohJGY"
web3 = Web3(Web3.HTTPProvider(RPC_URL))



def load_from_file(filename: str) -> List[str]:
    with Path(filename).open() as file:
        return [line.strip() for line in file if line.strip()]


private_keys = load_from_file("privateKey.txt")
access_tokens = load_from_file("token.txt")
proxies = load_from_file("proxies.txt")


assert len(private_keys) == len(access_tokens), "私钥和访问令牌的数量必须相同"


if len(proxies) < len(private_keys):
    proxies = list(itertools.cycle(proxies))[:len(private_keys)]


CONTRACT_ABI = json.loads('''
[
    {
        "constant": false,
        "inputs": [],
        "name": "depositETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]
''')


headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
}


async def get_proxy_ip(session: aiohttp.ClientSession) -> str:
    try:
        async with session.get('https://api.ipify.org', timeout=10) as response:
            return await response.text()
    except Exception as e:
        print(f"{Fore.RED}获取代理IP时出错: {str(e)}{Style.RESET_ALL}")
        return "未知"


async def colay(session: aiohttp.ClientSession, url: str, method: str, payload_data: Dict[str, Any] = None) -> \
Dict[str, Any]:
    async with session.request(method, url, headers=headers, json=payload_data) as response:
        if response.status != 200:
            raise Exception(f'HTTP错误！状态码: {response.status}')
        return await response.json()


async def refresh_access_token(session: aiohttp.ClientSession, refresh_token: str) -> str:
    api_key = "AIzaSyDipzN0VRfTPnMGhQ5PSzO27Cxm3DohJGY"
    async with session.post(
        f'https://securetoken.googleapis.com/v1/token?key={api_key}',
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f'grant_type=refresh_token&refresh_token={refresh_token}'
    ) as response:
        if response.status != 200:
            raise Exception("Failed to refresh access token")
        data = await response.json()
        return data.get('access_token')


async def handle_grow_and_garden(session: aiohttp.ClientSession, refresh_token: str, proxy: str) -> None:
    proxy_ip = await get_proxy_ip(session)
    print(f"{Fore.CYAN}当前使用的代理IP: {proxy_ip}{Style.RESET_ALL}")

    new_access_token = await refresh_access_token(session, refresh_token)
    headers['authorization'] = f'Bearer {new_access_token}'

    info_query = {
        "query": "query getCurrentUser { "
                 "currentUser { id totalPoint depositCount } "
                 "getGardenForCurrentUser { "
                 "gardenStatus { growActionCount gardenRewardActionCount } "
                 "} "
                 "}",
        "operationName": "getCurrentUser"
    }
    info = await colay(session, api_url, 'POST', info_query)

    balance = info['data']['currentUser']['totalPoint']
    deposit = info['data']['currentUser']['depositCount']
    grow = info['data']['getGardenForCurrentUser']['gardenStatus']['growActionCount']
    garden = info['data']['getGardenForCurrentUser']['gardenStatus']['gardenRewardActionCount']

    print(f"{Fore.GREEN}积分：{balance} | 存款次数：{deposit} | 剩余增长次数：{grow} | 剩余花园次数：{garden}{Style.RESET_ALL}")

    async def grow_action():
        grow_action_query = {
            "query": """
                  mutation executeGrowAction {
                      executeGrowAction(withAll: true) {
                          totalValue
                          multiplyRate
                      }
                      executeSnsShare(actionType: GROW, snsType: X) {
                          bonus
                      }
                  }
              """,
            "operationName": "executeGrowAction"
        }

        try:
            mine = await colay(session, api_url, 'POST', grow_action_query)

            if mine and 'data' in mine and 'executeGrowAction' in mine['data']:
                reward = mine['data']['executeGrowAction']['totalValue']
                return reward
            else:
                print(f"{Fore.RED}错误：响应格式异常：{mine}{Style.RESET_ALL}")
                return 0
        except Exception as e:

            return 0

    if grow > 0:

        reward = await grow_action()

        if reward:
            balance += reward
            grow = 0
            print(f"{Fore.GREEN}Rewards: {reward} | Balance: {balance} | Grow left: {grow}{Style.RESET_ALL}")

    while garden >= 10:
        garden_action_query = {
            "query": "mutation executeGardenRewardAction($limit: Int!) { executeGardenRewardAction(limit: $limit) { data { cardId group } isNew } }",
            "variables": {"limit": 10},
            "operationName": "executeGardenRewardAction"
        }
        mine_garden = await colay(session, api_url, 'POST', garden_action_query)
        card_ids = [item['data']['cardId'] for item in mine_garden['data']['executeGardenRewardAction']]
        print(f"{Fore.GREEN}Opened Garden: {card_ids}{Style.RESET_ALL}")
        garden -= 10


async def get_gas_price_strategy(web3, multiplier=1.1):
    gas_price = web3.eth.gas_price
    return int(gas_price * multiplier)


async def wait_for_transaction_receipt(web3, transaction_hash, max_attempts=10):
    attempts = 0
    while attempts < max_attempts:
        try:
            receipt = web3.eth.get_transaction_receipt(transaction_hash)
            if receipt is not None:
                return receipt
        except TransactionNotFound:
            pass
        attempts += 1
        await asyncio.sleep(1)
    return None


async def handle_eth_transactions(session: aiohttp.ClientSession, num_transactions: int, proxy: str) -> None:
    proxy_ip = await get_proxy_ip(session)
    print(f"{Fore.CYAN}当前使用的代理IP: {proxy_ip}{Style.RESET_ALL}")

    global nonces
    amount_wei = web3.to_wei(AMOUNT_ETH, 'ether')
    contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=json.loads(contract_abi))
    nonces = {key: web3.eth.get_transaction_count(web3.eth.account.from_key(key).address) for key in private_keys}
    for i in range(num_transactions):
        for private_key in private_keys:

            from_address = web3.eth.account.from_key(private_key).address
            short_from_address = from_address[:4] + "..." + from_address[-4:]

            try:
                transaction = contract.functions.depositETH().build_transaction({
                    'from': from_address,
                    'value': amount_wei,
                    'gas': 100000,
                    'gasPrice': web3.eth.gas_price,
                    'nonce': nonces[private_key],
                })

                signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
                tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                print(
                    f"{Fore.GREEN}Transaction {i + 1} sent from {short_from_address} with hash: {tx_hash.hex()}{Style.RESET_ALL}")

                nonces[private_key] += 1
                await asyncio.sleep(1)

            except Exception as e:
                if 'nonce too low' in str(e):
                    print(
                        f"{Fore.RED}Nonce too low for {short_from_address}. Fetching the latest nonce...{Style.RESET_ALL}")
                    nonces[private_key] = web3.eth.get_transaction_count(from_address)
                elif 'already known' in str(e):
                    print(
                        f"{Fore.RED}Nonce too low for {short_from_address}. Fetching the latest nonce...{Style.RESET_ALL}")
                    nonces[private_key] = web3.eth.get_transaction_count(from_address)
                elif 'replacement transaction underpriced' in str(e):
                    print(
                        f"{Fore.RED}Nonce too low for {short_from_address}. Fetching the latest nonce...{Style.RESET_ALL}")
                    nonces[private_key] = web3.eth.get_transaction_count(from_address)
                else:
                    print(f"{Fore.RED}Error sending transaction from {short_from_address}: {str(e)}{Style.RESET_ALL}")

async def main(mode: str, num_transactions: int = None) -> None:
    for i, (private_key, access_token, proxy) in enumerate(zip(private_keys, access_tokens, proxies)):
        print(f"{Fore.YELLOW}正在处理账户 {i + 1}{Style.RESET_ALL}")
        try:

            parsed_proxy = urlparse(proxy)
            proxy_type = ProxyType.SOCKS5 if parsed_proxy.scheme == 'socks5' else ProxyType.HTTP


            if not parsed_proxy.hostname or not parsed_proxy.port:
                raise ValueError(f"无效的代理URL: {proxy}")

            connector = ProxyConnector(
                proxy_type=proxy_type,
                host=parsed_proxy.hostname,
                port=parsed_proxy.port,
                username=parsed_proxy.username,
                password=parsed_proxy.password,
                rdns=True
            )

            async with aiohttp.ClientSession(connector=connector) as session:
                if mode == '1':
                    if num_transactions is None:
                        num_transactions = int(input(Fore.YELLOW + "输入要执行的交易数量: " + Style.RESET_ALL))
                    await handle_eth_transactions(session, num_transactions, proxy)
                elif mode == '2':
                    await handle_grow_and_garden(session, access_token, proxy)
                else:
                    print(Fore.RED + "选项无效。请选择1或2。" + Style.RESET_ALL)
        except ValueError as ve:
            print(f"{Fore.RED}处理账户 {i + 1} 时出错: 代理URL无效 - {str(ve)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}处理账户 {i + 1} 时出错: {str(e)}{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}账户 {i + 1} 处理完成{Style.RESET_ALL}")
        await asyncio.sleep(5)

    if mode == '2':
        print(f"{Fore.RED}所有账户均已处理。冷却10分钟...{Style.RESET_ALL}")
        await asyncio.sleep(600)


if __name__ == '__main__':
    print("----------------脚本由anni著作免费开源---------------------")
    print("----------------推特@lisa50902711142---------------------")
    print("----------------交流群https://t.me/annilumao---------------------")
    parser = argparse.ArgumentParser(description='选择操作模式。')
    parser.add_argument('-a', '--action', choices=['1', '2'], help='1：执行交易，2：耕种')
    parser.add_argument('-tx', '--transactions', type=int, help='要执行的交易数（操作1可选）')

    args = parser.parse_args()

    if args.action is None:
        args.action = input(Fore.YELLOW + "选择操作（1：执行交易，2：耕种）： " + Style.RESET_ALL)
        while args.action not in ['1', '2']:
            print(Fore.RED + "选择无效。请选择1或2。" + Style.RESET_ALL)
            args.action = input(Fore.YELLOW + "选择操作（1：执行交易，2：耕种）： " + Style.RESET_ALL)

    asyncio.run(main(args.action, args.transactions))