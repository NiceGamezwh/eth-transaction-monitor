import json
from web3 import Web3
import time
from eth_account import Account
import signal
import sys
import os
from datetime import datetime
import asyncio
import aiohttp

# 读取配置文件
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    INFURA_API_KEY = config["infura_api_key"]
except FileNotFoundError:
    print("错误: config.json 文件不存在！")
    sys.exit(1)
except KeyError:
    print("错误: config.json 中缺少 'infura_api_key' 字段！")
    sys.exit(1)
except Exception as e:
    print(f"加载 config.json 失败: {e}")
    sys.exit(1)

# 配置 Infura 节点
INFURA_URL_ETH = f"https://sepolia.infura.io/v3/{INFURA_API_KEY}"
INFURA_URL_ARB = f"https://arbitrum-sepolia.infura.io/v3/{INFURA_API_KEY}"

# 创建 Web3 实例
w3_eth = Web3(Web3.HTTPProvider(INFURA_URL_ETH, request_kwargs={'timeout': 30}))
w3_arb = Web3(Web3.HTTPProvider(INFURA_URL_ARB, request_kwargs={'timeout': 30}))

# 验证 Web3 连接
if not w3_eth.is_connected():
    print("错误: 以太坊 Sepolia 网络连接失败！")
    sys.exit(1)
if not w3_arb.is_connected():
    print("错误: Arbitrum Sepolia 网络连接失败！")
    sys.exit(1)

# 统一的目标地址
TARGET_ADDRESS = "0x07c1d51325ec31477bc13493bc71cFe9075C3828"
TARGET_ADDRESS = w3_eth.to_checksum_address(TARGET_ADDRESS)

# 从文件加载地址
def load_addresses_from_file(filename="addresses.json"):
    try:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"{filename} 文件不存在！")
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载 {filename} 失败: {e}")
        sys.exit(1)

# 验证地址
def validate_addresses(address_list, network):
    validated_addresses = []
    w3 = w3_eth if network == "eth" else w3_arb
    for addr in address_list:
        try:
            addr["source_address"] = w3.to_checksum_address(addr["source_address"])
            account = Account.from_key(addr["private_key"])
            if account.address.lower() != addr["source_address"].lower():
                raise ValueError(f"地址 {addr['source_address']} 与私钥不匹配！")
            validated_addresses.append(addr)
        except Exception as e:
            print(f"地址验证失败: {addr['source_address']} - {e}")
    return validated_addresses

def get_nonce(address, network):
    w3 = w3_eth if network == "eth" else w3_arb
    for _ in range(3):
        try:
            return w3.eth.get_transaction_count(address, 'pending')
        except Exception as e:
            print(f"[{address}] 获取 nonce 失败: {e}, 重试中...")
            time.sleep(1)
    raise Exception(f"[{address}] 获取 nonce 失败，已达最大重试次数")

def send_transaction(private_key, source_address, network):
    try:
        w3 = w3_eth if network == "eth" else w3_arb
        balance_wei = w3.eth.get_balance(source_address)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{source_address}] {timestamp} 当前余额: {balance_wei / 10**18} ETH")

        gas_price = int(w3.eth.gas_price * 1.2)
        gas_limit = 21000
        total_gas_cost = gas_limit * gas_price

        if balance_wei <= total_gas_cost:
            print(f"[{source_address}] {timestamp} 余额不足以支付 Gas 费用: {total_gas_cost / 10**18} ETH")
            return None

        max_value_wei = balance_wei - total_gas_cost
        print(f"[{source_address}] {timestamp} 可转出金额: {max_value_wei / 10**18} ETH")

        nonce = get_nonce(source_address, network)
        tx = {
            'nonce': nonce,
            'to': TARGET_ADDRESS,
            'value': max_value_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': 11155111 if network == "eth" else 421614
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"[{source_address}] {timestamp} 交易已发送，哈希: {tx_hash.hex()}")
        return tx_hash.hex()

    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{source_address}] {timestamp} 发送交易失败: {e}")
        return None

# 异步获取区块
async def fetch_block(w3, block_num):
    try:
        block = w3.eth.get_block(block_num, full_transactions=True)
        return block
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] 获取区块 {block_num} 失败: {e}")
        return None

# 异步监控和转账
async def monitor_and_transfer_async():
    global addresses
    addresses = load_addresses_from_file()
    
    addresses_eth = validate_addresses(addresses, "eth")
    addresses_arb = validate_addresses(addresses, "arb")

    if not addresses_eth and not addresses_arb:
        print("错误: 没有有效的地址可监控！")
        return

    print(f"开始监控 {len(addresses_eth)} 个以太坊地址和 {len(addresses_arb)} 个 Arbitrum 地址...")
    last_block_eth = w3_eth.eth.block_number
    last_block_arb = w3_arb.eth.block_number

    while True:
        try:
            current_block_eth = w3_eth.eth.block_number
            current_block_arb = w3_arb.eth.block_number

            # 并行检查两个网络的区块
            async def check_eth_blocks():
                nonlocal last_block_eth
                if current_block_eth > last_block_eth:
                    for block_num in range(last_block_eth + 1, current_block_eth + 1):
                        block_eth = await fetch_block(w3_eth, block_num)
                        if block_eth:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            for addr in addresses_eth:
                                for tx in block_eth.transactions:
                                    if tx['to'] and tx['to'].lower() == addr['source_address'].lower():
                                        value_eth = tx['value'] / 10**18
                                        delay = (datetime.now() - datetime.fromtimestamp(block_eth['timestamp'])).total_seconds()
                                        print(f"[{addr['source_address']}] {timestamp} 检测到转入 (区块 {block_num}): {value_eth} ETH (来自 {tx['from']}), 延迟: {delay:.2f} 秒")
                                        tx_hash = send_transaction(addr["private_key"], addr["source_address"], "eth")
                                        if tx_hash:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                            print(f"[{addr['source_address']}] {timestamp} 成功转账到 {TARGET_ADDRESS}, 哈希: {tx_hash}")
                                        else:
                                            print(f"[{addr['source_address']}] {timestamp} 转账失败！")
                    last_block_eth = current_block_eth

            async def check_arb_blocks():
                nonlocal last_block_arb
                if current_block_arb > last_block_arb:
                    for block_num in range(last_block_arb + 1, current_block_arb + 1):
                        block_arb = await fetch_block(w3_arb, block_num)
                        if block_arb:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            for addr in addresses_arb:
                                for tx in block_arb.transactions:
                                    if tx['to'] and tx['to'].lower() == addr['source_address'].lower():
                                        value_eth = tx['value'] / 10**18
                                        delay = (datetime.now() - datetime.fromtimestamp(block_arb['timestamp'])).total_seconds()
                                        print(f"[{addr['source_address']}] {timestamp} 检测到转入 (区块 {block_num}): {value_eth} ETH (来自 {tx['from']}), 延迟: {delay:.2f} 秒")
                                        tx_hash = send_transaction(addr["private_key"], addr["source_address"], "arb")
                                        if tx_hash:
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                            print(f"[{addr['source_address']}] {timestamp} 成功转账到 {TARGET_ADDRESS}, 哈希: {tx_hash}")
                                        else:
                                            print(f"[{addr['source_address']}] {timestamp} 转账失败！")
                    last_block_arb = current_block_arb

            await asyncio.gather(check_eth_blocks(), check_arb_blocks())

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 网络请求失败: {e}, 正在重试...")
            await asyncio.sleep(1)

        await asyncio.sleep(0.1)  # 轮询间隔保持 0.1 秒

def signal_handler(sig, frame):
    print('\n你按下了 Ctrl+C，正在退出...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    asyncio.run(monitor_and_transfer_async())