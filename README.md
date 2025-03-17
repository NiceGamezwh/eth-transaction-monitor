# Ethereum and Arbitrum Transaction Monitor

这是一个用于监控指定多个地址在多个网络交易的 Python 脚本。当检测到指定地址收到转账时，它会自动将资金（扣除gas的最大值）最快速度转出到目标地址（高于当前gas20%以求最快交易，可动态调整）。

## 功能
- **实时监控**：监控Sepolia ETH 和 Arbitrum Sepolia 网络上指定多个地址的转入交易。
- **自动转账**：检测到转入后，自动将可用余额（扣除 Gas 费用）转到预设目标地址。
- **延迟优化**：使用异步 HTTP 轮询，检测延迟通常在 5-10 秒以内（取决于节点同步速度）。
- **日志输出**：记录转入检测、余额、交易发送和结果，便于调试和跟踪。

## 先决条件
- Python 3.6 或更高版本。
- 一个有效的 Infura API Key（在 [Infura](https://infura.io/) 注册获取）。
- 已配置的 `config.json` 和 `addresses.json` 文件。

## 安装
1. **克隆仓库**：
   ```bash
   git clone https://github.com/NiceGamezwh/eth-transaction-monitor.git
   cd eth-transaction-monitor
1. **安装依赖**：
   ```bash
   gpip3 install aiohttp web3
## 配置
1. **创建config.json**：
   ```bash
   {
    "infura_api_key": "你的InfuraAPIKey"
   }
1. **创建addresses.json**：
   ```bash
   [
    {
        "private_key": "你的钱包私钥1",
        "source_address": "私钥1对应的地址"
    },
    {
        "private_key": "你的钱包私钥2",
        "source_address": "私钥2对应的地址"
    }
   ]
## 使用
1. **运行脚本**：
   ```bash
   python3 monitor_transfer.py
1. **输出实例**：

   开始监控 2 个以太坊地址和 2 个 Arbitrum 地址...  

   [0xedea7B5D...] 2025-03-17 13:00:05.123 检测到转入 (区块 133082010): 0.001 ETH (来自 0x07C1D513...), 延迟: 4.50 秒  

   [0xedea7B5D...] 2025-03-17 13:00:05.234 当前余额: 0.001 ETH  

   [0xedea7B5D...] 2025-03-17 13:00:05.234 可转出金额: 0.000979 ETH  

   [0xedea7B5D...] 2025-03-17 13:00:05.234 交易已发送，哈希: 0x1234...  

   [0xedea7B5D...] 2025-03-17 13:00:06.345 成功转账到 0x07C1D513..., 哈希: 0x1234...  


### 停止脚本：
按 `Ctrl+C` 退出。

## 注意事项
- **安全性**：`config.json` 和 `addresses.json` 包含敏感信息（API Key 和私钥）。
- **延迟**：检测延迟取决于 Infura 节点的同步速度。如果需要更低延迟，可尝试切换到 Alchemy 节点或使用 WebSocket。
- **测试网**：该脚本支持 Sepolia ETH 和 Arbitrum Sepolia 测试网，其他任意网络可以自行添加。

## 贡献
欢迎提交问题或改进建议！请通过 GitHub Issues 联系。

## 作者
GitHub: [NiceGamezwh](https://github.com/NiceGamezwh)
