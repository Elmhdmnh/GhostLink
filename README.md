# Remote Admin Toolkit (RAT) / 远程管理工具

A lightweight Python-based remote administration toolkit with Shell command execution, real-time screen monitoring, camera capture, and file system management.
基于 Python 的轻量级远程管理工具，支持 Shell 命令执行、屏幕实时监控、摄像头画面采集和文件系统管理。

> ⚠️ **Disclaimer / 免责声明**: This project is for security research and educational purposes only. Do not use for unauthorized access. Users must comply with local laws and assume all responsibility.
> 本项目仅供安全研究和教育用途，请勿用于未经授权的访问。使用者需遵守当地法律法规，自行承担所有责任。

## Features / 功能特性

- **Remote Shell / 远程 Shell** — Execute arbitrary commands on client, supports `cd` directory switching / 在服务端对客户端执行任意命令，支持 `cd` 目录切换
- **Screen Monitor / 屏幕监控** — Real-time client screen capture, in-memory processing (no disk writes) / 实时获取客户端屏幕截图，内存处理不落盘
- **Camera Monitor / 摄像头监控** — Remotely open client camera with live video feed / 远程开启客户端摄像头，实时回传画面
- **File Manager / 文件管理** — Browse directories, download & delete files on client / 浏览客户端磁盘目录，下载和删除文件
- **Multi-Client / 多客户端管理** — Manage multiple connected clients, switch by index number / 支持同时连接多个客户端，通过编号切换
- **Resizable Window / 可调整窗口** — Monitor windows support free resizing / 监控窗口支持自由缩放
- **Auto Reconnect / 自动重连** — Client automatically reconnects after disconnection / 客户端断线后自动重连

## Architecture / 架构概览

```
┌──────────────┐     TCP:8080     ┌──────────────────┐
│   后台.py     │ ◄──────────────► │    客户端.py      │
│  (Controller) │                  │   (Agent)        │
│              │                  │                   │
│  ┌────────┐  │   1-byte opcode  │  ┌─────────────┐  │
│  │ Menu   │──┼────────────────►│  │ Shell Module │  │
│  │ Control│  │                  │  │Screen Module │  │
│  │ Display│  │ 8-byte len+data  │  │Camera Module │  │
│  │        │◄─┼─────────────────│  │ File Module  │  │
│  └────────┘  │                  │  └─────────────┘  │
└──────────────┘                  └──────────────────┘
```

## Protocol / 通信协议

| Step | Direction | Content | Description |
|------|-----------|---------|-------------|
| 1 | Server → Client | `1` / `2` / `3` / `4` | 1-byte mode code: Shell / Screen / Camera / File |
| 2 | Server ↔ Client | Command string | Interactive commands (`get` for frame, `stop` to end, Shell commands, `look`/`get`/`delete` for files, etc.) |
| 3 | Client → Server | `8-byte length header + data body` | Command output, JPEG image data, or pickled file list |

## Requirements / 环境要求

- **Python** >= 3.8
- **OS**: Windows / Linux / macOS

### Install Dependencies / 依赖安装

```bash
pip install opencv-python numpy pillow pywin32
```

> Both server and client need the above dependencies. `pywin32` is required on Windows for file system operations. / 服务端和客户端都需要安装以上依赖。Windows 下需要 `pywin32` 以支持文件系统操作。

## Usage / 使用说明

### 1. Configure Client / 配置客户端

Edit `客户端.py` and set the target IP address:

```python
IP, PORT = '192.168.0.106', 8080  # Change to backend server IP / 改为后台服务器地址
```

### 2. Start Backend / 启动后台 (Controller / 控制端)

```bash
python 后台.py
```

```
Server started, waiting for clients...

--- Admin Menu ---
list               - List all online clients
shell <number>     - Send Shell command to client
screen <number>    - Start screen monitoring
camera <number>    - Open client camera
file   <number>    - Browse client file system
quit               - Exit
Enter command:
```

### 3. Start Client / 启动客户端 (Agent / 被控端)

```bash
python 客户端.py
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

# File manager (type 0 to exit) / 文件管理 (输入 0 退出)
file 1
```

#### File Manager Commands / 文件管理命令

| Command | Example | Description |
|---------|---------|-------------|
| `to <drive>` | `to C:` | Navigate to a drive / 导航到磁盘 |
| `to <drive> <dirs>` | `to C: Users Admin` | Navigate to a subdirectory / 导航到子目录 |
| `back` | `back` | Go up one directory / 返回上级目录 |
| `look` | `look` | List current directory / 列出当前目录 |
| `look <subdir>` | `look Documents` | List subdirectory / 列出子目录 |
| `get <filename>` | `get secret.txt` | Download file to local / 下载文件到本地 |
| `delete <filename>` | `delete log.txt` | Delete file on client / 删除客户端文件 |
| `0` | `0` | Return to main menu / 返回主菜单 |

## Project Structure / 项目结构

```
├── 后台.py           # Controller - Admin menu & display / 控制端
├── 客户端.py         # Agent - Execute commands & send data / 被控端
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
| `4` | File | `look <path>` list dir / `get <path>` download / `delete <path>` remove / `0` exit |

### File Module Protocol / 文件管理协议

```
Server ──► Client:  "4"                         (进入文件管理模式)
Server ◄── Client:  "00000030C:\D:\E:\"         (8字节长度头 + 磁盘列表)
Server ──► Client:  "look C:\"                  (列出目录)
Server ◄── Client:  "00000123<pickle_data>"     (8字节长度头 + pickle序列化的文件列表)
Server ──► Client:  "get C:\secret.txt"         (下载文件)
Server ◄── Client:  "00001024"                  (8字节文件大小)
Server ──► Client:  "ok"                        (确认接收)
Server ◄── Client:  <file_bytes>               (文件原始字节)
Server ──► Client:  "delete C:\log.txt"         (删除文件)
Server ──► Client:  "0"                         (退出文件管理模式)
```

## Author / 作者

**Elmh**

