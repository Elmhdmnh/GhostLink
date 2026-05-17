# Remote Admin Toolkit (RAT) / 远程管理工具

A lightweight Python-based remote administration toolkit with Shell command execution, real-time screen monitoring, and camera capture.
基于 Python 的轻量级远程管理工具, 支持 Shell 命令执行, 屏幕实时监控和摄像头画面采集.

> ⚠️ **Disclaimer / 免责声明**: This project is for security research and educational purposes only. Do not use for unauthorized access. Users must comply with local laws and assume all responsibility.
> 本项目仅供安全研究和教育用途, 请勿用于未经授权的访问. 使用者需遵守当地法律法规, 自行承担所有责任.

## Features / 功能特性

- **Remote Shell / 远程 Shell** -- Execute arbitrary commands on client, supports `cd` directory switching / 在服务端对客户端执行任意命令, 支持 `cd` 目录切换
- **Screen Monitor / 屏幕监控** -- Real-time client screen capture, in-memory processing (no disk writes) / 实时获取客户端屏幕截图, 内存处理不落盘
- **Camera Monitor / 摄像头监控** -- Remotely open client camera with live video feed / 远程开启客户端摄像头, 实时回传画面
- **Multi-Client / 多客户端管理** -- Manage multiple connected clients, switch by index number / 支持同时连接多个客户端, 通过编号切换
- **Resizable Window / 可调整窗口** -- Monitor windows support free resizing / 监控窗口支持自由缩放
- **Auto Reconnect / 自动重连** -- Client automatically reconnects after disconnection / 客户端断线后自动重连

## Architecture / 架构概览

```
┌──────────────┐     TCP:8080     ┌──────────────────┐
│  backend.py   │ ◄──────────────► │   client.py      │
│  (Controller) │                  │   (Agent)        │
│              │                  │                   │
│  ┌────────┐  │   1-byte opcode  │  ┌─────────────┐  │
│  │ Menu   │──┼────────────────►│  │ Shell Module │  │
│  │ Control│  │                  │  │Screen Module │  │
│  │ Display│  │ 8-byte len+data  │  │Camera Module │  │
│  │        │◄─┼─────────────────│  │             │  │
│  └────────┘  │                  │  └─────────────┘  │
└──────────────┘                  └──────────────────┘
```

## Protocol / 通信协议

| Step | Direction | Content | Description |
|------|-----------|---------|-------------|
| 1 | Server → Client | `1` / `2` / `3` | 1-byte mode code: Shell / Screen / Camera |
| 2 | Server ↔ Client | Command string | Interactive commands (`get` for frame, `stop` to end, Shell commands, etc.) |
| 3 | Client → Server | `8-byte length header + data body` | Command output or JPEG image data |

## Requirements / 环境要求

- **Python** >= 3.8
- **OS**: Windows / Linux / macOS

### Install Dependencies / 依赖安装

```bash
pip install opencv-python numpy pillow
```

> Both server and client need the above dependencies. / 服务端和客户端都需要安装以上依赖.

## Usage / 使用说明

### 1. Configure Client / 配置客户端

Edit `client.py` and set the target IP address:

```python
IP, PORT = '192.168.0.106', 8080  # Change to backend server IP / 改为后台服务器地址
```

### 2. Start Backend / 启动后台 (Controller / 控制端)

```bash
python backend.py
```

```
Server started, waiting for clients...

--- Admin Menu ---
list               - List all online clients
shell <number>     - Send Shell command to client
screen <number>    - Start screen monitoring
camera <number>    - Open client camera
quit               - Exit
Enter command:
```

### 3. Start Client / 启动客户端 (Agent / 被控端)

```bash
python client.py
```

The client will connect automatically and wait for commands. / 客户端会自动连接并等待指令.

### 4. Commands / 操作命令

```bash
# List online clients / 查看在线客户端
list

# Remote Shell (type 0 to exit) / 远程 Shell (输入 0 退出)
shell 1

# Screen monitor (press q to exit) / 屏幕监控 (按 q 键退出)
screen 1

# Camera monitor (press q to exit) / 摄像头监控 (按 q 键退出)
camera 1

# Quit / 退出程序
quit
```

## Project Structure / 项目结构

```
├── backend.py        # Controller - Admin menu & display / 控制端
├── client.py         # Agent - Execute commands & send data / 被控端
├── README.md         # Documentation / 项目说明
├── LICENSE           # MIT License
└── requirements.txt  # Python dependencies / 依赖列表
```

## Protocol Details / 协议细节

### Opcodes / 命令码

| Code | Module | Sub-commands |
|------|--------|--------------|
| `1` | Shell | Any system command, send `0` to exit |
| `2` | Screen | `get` to capture one frame / `stop` to end |
| `3` | Camera | `get` to capture one frame / `stop` to end |

### Data Format / 数据传输格式

All responses use `8-byte fixed-length header + data body` format:

```
┌────────────────────┬─────────────────────┐
│  8-byte header     │     Data body       │
│  "00001024"        │  (1024 bytes data)  │
└────────────────────┴─────────────────────┘
```

## Author / 作者

**Elmh**

