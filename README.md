# 								HanaNetwotk

## 描述

**支持多账户**

- 在此注册：https://hanafuda.hana.network/dashboard

- 在 Google 上注册

- 提交代码

  ```
  O7WHLE
  ```

  

- 向 ETH BASE 存入 1 美元，但不要太多。

- 进行 5,000 笔交易，每小时赚取 300 元（解锁卡并获得积分）。

- 进行 10,000 笔交易即可获得 643 个花园奖励盒（以解锁收藏卡）。

**如果你已经解锁收藏卡结束脚本**

## 安装



```
git clone https://github.com/cc1104666/HanaNetwotk
cd HanaNetwork
```



安装软件包

```
pip install -r requirements.txt
```



**编辑pvkey.txt，输入私钥**

```
privateKey.txt
```



运行脚本

```
python3 hana.py
```



**选择1进行交易**

## 运行种植并打开花园箱



**首先你需要获取刷新令牌**

- 打开 Hana 仪表板：https://hanafuda.hana.network/dashboard
- 单击 F12 打开控制台
- 找到应用程序并选择会话存储
- 选择 hana 并复制你的 refreshToken![img](https://cdn.nlark.com/yuque/0/2024/png/40368878/1731217135637-6b2ce886-181b-4d4c-9bfa-92807eef74a9.png)
- 编辑 token.txt 粘贴您的刷新令牌

运行脚本

```
python3 main.py -a 2
```

## 您也可以使用 pm2 在后台运行脚本



您可以使用 pm2 在后台运行脚本，这样即使您关闭终端后它仍能继续运行。

### 安装 pm2



如果你尚未安装 pm2，则可以使用 npm 全局安装：

```
npm install -g pm2
```



### 使用 pm2 启动脚本



运行脚本来执行 1000 个交易：

```
pm2 start hana.py --name "hana-tx" --interpreter python3 -- -a 1 -tx 1000
```



要进行种植和园艺活动：

```
pm2 start hana.py --name "hana-grow" --interpreter python3 -- -a 2
```



## 管理 pm2 进程



您可以使用以下命令管理您的 pm2 进程：

- 列出正在运行的进程：

```
pm2 list
```



- 重新启动一个进程：

```
pm2 restart hana-tx
```



- 停止进程：

```
pm2 stop hana-tx
```



- 查看日志：

```
pm2 logs hana-tx
```

如果你也觉得不错的话可以请我喝杯咖啡：

EVM：0xbf0b70FAE3A32fbFe32a8CFdd461Bd63Bdf9D4B7