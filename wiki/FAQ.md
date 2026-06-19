# 常见问题

---

## 连接与网络

### Q: 客户端连接不上控制端？

**检查清单：**

1. 确认控制端已先启动：`python 后台.py`
2. 确认客户端 `IP` 地址配置正确（`客户端.py` 第 21 行）
3. 确认端口一致（默认 `4444`）
4. 检查防火墙是否放行了 `4444` 端口
5. 如果通过互联网连接，确认已做端口映射/转发

### Q: 如何修改监听端口？

同时修改两个文件中的 `PORT` 变量：

```python
# 后台.py
PORT = 4444  # 改为你想要的端口

# 客户端.py
IP, PORT = '192.168.0.103', 4444  # 端口与控制端一致
```

### Q: 客户端断开后会自动重连吗？

会。客户端捕获连接异常后等待 5 秒自动重连：

```python
except Exception as e:
    time.sleep(5)  # 断线后自动重连
```

### Q: 为什么端口要设 `SO_REUSEADDR`？

```python
backend.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

允许控制端重启时立即绑定端口，避免因 `TIME_WAIT` 状态导致的 "Address already in use" 错误。

---

## 功能使用

### Q: Shell 中执行 `cd` 命令无效？

Shell 模块内置了对 `cd` 的特殊处理。使用 `cd C:\path` 格式即可：

```text
Shell> cd C:\Users
CWD: C:\Users
```

底层通过 `os.chdir()` 实现目录切换，而非启动子进程。

### Q: 屏幕/摄像头窗口无法关闭？

在 OpenCV 显示窗口中按键盘 `q` 键（小写）。确保：
- 输入法为英文状态
- OpenCV 窗口处于激活（焦点）状态

### Q: 摄像头画面是黑屏？

可能原因：
1. 客户端没有摄像头硬件
2. 摄像头被其他程序占用
3. 摄像头权限未授予 Python

客户端设计了容错机制，摄像头失败时会发送空帧而不崩溃。

### Q: 文件管理中的 `send` 命令没有反应？

`send` 命令会弹出 `tkinter` 文件选择对话框。确保：
- 控制端运行在有图形界面的系统上
- 如果远程 SSH 到控制端，`tkinter` 无法弹出 GUI 窗口

### Q: `information` 命令中某些字段显示"无法获取"？

部分字段依赖特定条件：
- NTFS 字段（#37-40）：仅在 NTFS 文件系统上可用
- 版本信息（#24-31）：仅 PE 文件（.exe/.dll）可用
- SHA256 哈希（#10）：大文件可能较慢
- ADS 数据流（#40）：仅 NTFS 且需要相应权限

### Q: 键盘记录获取不到数据？

键盘记录依赖 `pynput` 库的后台监听。确认：
1. 客户端环境安装了 `pynput>=1.7.0`
2. 客户端以管理员权限运行（键盘钩子可能需要管理员权限）
3. 客户端在被控期间有按键操作

---

## 环境与依赖

### Q: 支持 macOS/Linux 吗？

控制端（`后台.py`）基本可以在 macOS/Linux 上运行，但有以下限制：
- 文件管理中的 `pywin32` 相关功能不可用
- 屏幕截图可能不支持（依赖 `ImageGrab`）

客户端（`客户端.py`）的许多功能依赖 Windows API（`pywin32`、`win32api`、`ctypes.windll`），在非 Windows 系统上无法正常运行。

### Q: 安装 `pywin32` 报错？

```bash
# 尝试指定版本
pip install pywin32==306

# 或使用国内镜像
pip install pywin32 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: `opencv-python` 导入报错？

```bash
# 尝试安装 headless 版本（无 GUI 依赖）
pip uninstall opencv-python
pip install opencv-python-headless
```

注意：headless 版本不支持 `cv2.imshow()`，控制端将无法显示图像窗口。

---

## 安全与隐私

### Q: 通信是否加密？

当前版本通信为**明文 TCP**，未实现加密。数据在传输过程中未受保护。

> 仅用于安全研究和教育目的。在生产或敏感环境中使用时请自行添加 TLS/SSL 层。

### Q: 客户端被安全软件拦截怎么办？

GhostLink 使用标准 Python 库实现功能，不包含恶意代码。但以下行为可能触发安全软件告警：
- 键盘钩子（`pynput`）
- 屏幕截图（`ImageGrab`）
- 摄像头访问（`cv2.VideoCapture`）
- 管理员提权（`ShellExecuteW runas`）

建议在测试环境中将相关目录加入安全软件的白名单。

### Q: 如何静默运行客户端？

客户端已内置以下静默特性：
- 管理员提权时窗口状态设为 `SW_HIDE (0)`
- 没有不必要的 `print()` 输出
- 后台线程无需用户交互

如需进一步隐藏，可考虑：
- 使用 `pythonw.exe` 运行（无控制台窗口）
- 打包为 Windows 服务
- 使用 PyInstaller 打包为 `.exe` 并设置 `--noconsole`

---

## 开发与扩展

### Q: 如何添加新的功能模块？

1. 在 `后台.py` 中新增处理函数（如 `handle_xxx`）
2. 分配新的操作码（如 `6`）
3. 在 `admin_console()` 菜单中添加选项
4. 在 `客户端.py` 中添加对应的 `elif choice == '6':` 分支

### Q: 如何修改截图质量？

修改 `客户端.py` 中的 quality 参数：

```python
# 屏幕截图 quality
img.save(img_byte_arr, format='JPEG', quality=30)  # 改为更高/更低

# 摄像头 quality
cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
```

quality 值越高画质越好，但数据量越大、传输越慢。

### Q: 如何打包为 exe？

```bash
pip install pyinstaller

# 打包客户端
pyinstaller --onefile --noconsole --hidden-import=pynput 客户端.py

# 打包控制端
pyinstaller --onefile 后台.py
```

> 打包后 `sys.frozen` 为 `True`，提权逻辑会自动适配。
