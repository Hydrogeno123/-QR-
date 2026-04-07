# 基于视觉密码学的QR码认证方案

## 项目简介

本项目实现了基于视觉密码学（Visual Cryptography, VC）的QR码认证系统。通过将秘密QR码分割成两个或多个视觉份额，只有当所有份额叠加在一起时才能恢复出原始的QR码进行认证。

## 视觉密码学原理

视觉密码学是一种将秘密图像加密成多个份额的技术，具有以下特点：

- **单份额无信息**：单独的任何一个份额都不包含任何可识别的秘密信息
- **叠加恢复**：只有将所有份额正确叠加在一起，才能通过人眼或设备恢复出秘密
- **无需计算**：恢复过程仅需物理叠加，无需复杂的解密计算

## 目录结构

```
sfrz1/
├── Basic_Output/              # 基础方案输出
├── Scheme1_BVC/               # 方案1：基础VC
├── Scheme2_OneMeaningful/     # 方案2：单有意义份额
├── Scheme3_TwoMeaningful/     # 方案3：双有意义份额
├── main.py                     # 基础方案实现
├── advanced_schemes.py         # 三种高级方案实现
├── requirements.txt            # 依赖包
└── README.md                   # 本文档
```

## 生成图片说明

### Basic_Output/ - 基础方案输出

| 文件名 | 说明 |
|--------|------|
| `1_Original_Secret_QR.png` | 原始秘密QR码，包含认证令牌信息，用于验证整个流程 |
| `2_Share1_Server.png` | 服务器端份额（Share 1），存储在服务器，单独看是随机噪声 |
| `3_Share2_Mobile.png` | 移动端份额（Share 2），分发给用户设备，单独看是随机噪声 |
| `4_Stacked_Combined.png` | 两个份额叠加后的图像，通过人眼可隐约看到QR码轮廓 |
| `5_Restored_QR.png` | 恢复后的QR码，可被QR码扫描器读取并认证 |

### Scheme1_BVC/ - 方案1：基础视觉密码学

| 文件名 | 说明 |
|--------|------|
| `1_Share1_Server.png` | 服务器端份额，纯随机噪声，不含任何可识别信息 |
| `2_Share2_Mobile.png` | 移动端份额，纯随机噪声，不含任何可识别信息 |
| `3_Stacked_Combined.png` | 两个份额叠加后的图像，呈现秘密QR码 |
| `4_Restored_Secret_QR.png` | 恢复处理后的秘密QR码，可直接扫描认证 |

### Scheme2_OneMeaningful/ - 方案2：单有意义份额

| 文件名 | 说明 |
|--------|------|
| `1_Share1_Server.png` | 服务器端份额，包含有意义的公开QR码信息 |
| `2_Share2_Mobile.png` | 移动端份额，随机噪声 |
| `3_Stacked_Combined.png` | 两个份额叠加后的图像，恢复出秘密QR码 |
| `4_Restored_Secret_QR.png` | 恢复处理后的秘密QR码 |

### Scheme3_TwoMeaningful/ - 方案3：双有意义份额

| 文件名 | 说明 |
|--------|------|
| `1_Share1_Server.png` | 服务器端份额，包含有意义的公开QR码（如商家信息） |
| `2_Share2_Mobile.png` | 移动端份额，包含有意义的公开QR码（如用户信息） |
| `3_Stacked_Combined.png` | 两个份额叠加后的图像，恢复出秘密QR码 |
| `4_Restored_Secret_QR.png` | 恢复处理后的秘密QR码 |

## 实现的三种方案

### Scheme 1: 基础视觉密码学（Basic VC）

两个份额均为随机噪声，单独看起来毫无意义。只有叠加后才能恢复出秘密QR码。

**特点**：最高安全性，任何单份额都无信息泄露风险

**文件位置**：`Scheme1_BVC/`

### Scheme 2: 单有意义份额

Share 1 是一个有意义的QR码（公开信息），Share 2 是随机噪声。叠加后恢复出秘密QR码。

**特点**：一个份额看起来是正常QR码，更具迷惑性

**文件位置**：`Scheme2_OneMeaningful/`

### Scheme 3: 双有意义份额

两个份额都是有意义的QR码（公开信息）。叠加后恢复出秘密QR码。

**特点**：两个份额都是正常QR码，隐蔽性最好

**文件位置**：`Scheme3_TwoMeaningful/`

## 环境要求

```
Python 3.7+
qrcode
numpy
opencv-python
Pillow
pyzbar
```

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install qrcode numpy opencv-python Pillow pyzbar
```

## 快速开始

### 运行基础方案

```bash
python main.py
```

输出到 `Basic_Output/` 文件夹，包含5张图片（详见上文"生成图片说明"）。

### 运行高级方案

```bash
python advanced_schemes.py
```

会生成三个方案的文件夹，每个文件夹包含4张图片（详见上文"生成图片说明"）。

## 使用流程

### 认证流程

1. **生成阶段**：服务器将认证令牌生成秘密QR码，并分割成两个份额
2. **分发阶段**：
   - Share 1 存储在服务器端
   - Share 2 分发给用户的移动设备
3. **认证阶段**：
   - 用户出示移动设备上的 Share 2
   - 服务器将 Share 1 和 Share 2 叠加
   - 扫描恢复的QR码进行认证

## 代码结构

### main.py

基础实现，包含：
- `VcQrAuthenticator` 类：核心认证类
- `generate_secret_qr()`：生成秘密QR码
- `encrypt_shares()`：分割成两个份额
- `combine_shares()`：叠加份额
- `decrypt_qr()`：恢复QR码
- `authenticate()`：认证验证

### advanced_schemes.py

高级实现，包含三种方案：
- `scheme_1_bvc()`：基础VC方案
- `scheme_2_one_meaningful()`：单有意义份额方案
- `scheme_3_two_meaningful()`：双有意义份额方案

## 技术特点

- **高安全性**：单个份额无法恢复任何信息
- **易于使用**：恢复过程只需叠加
- **QR码兼容**：使用标准QR码，可被普通设备扫描
- **错误容忍**：QR码自带纠错功能，恢复的图像仍可识别

## 应用场景

- 双因素认证
- 安全支付验证
- 访问控制
- 身份验证
- 防伪验证

## 示例输出

运行 `main.py` 后会看到：

```
=== QR Code + Visual Cryptography Authentication System ===
[*] Generated Original Secret QR Code.
[*] Encrypted into Share 1 (Server) and Share 2 (Mobile App).
[*] Combined Shares (Stacked).
[*] Restored QR Code for Scanning.
[+] Authentication SUCCESSFUL! Token matched: USER_AUTH_TOKEN_778899
```

## 参考文献

本实现基于视觉密码学的经典理论和QR码技术的结合应用。

## 许可证

本项目仅供学习和研究使用。
