# 基于视觉密码学的 QR 认证系统（论文思路对齐版）

## 1. 项目目标与定位

本项目实现了“二维码 + 视觉密码学（Visual Cryptography, VC）”认证流程，核心目标是：

1. 把一个秘密 QR（认证令牌）拆成两个份额（share）。
2. 单个份额不应泄露秘密内容。
3. 两个份额叠加后恢复出可扫码的秘密 QR。
4. 在高级方案中，引入“载体 QR / 背景图 / ROI / 显著性 / 纠错预算”提升隐蔽性。

当前代码由两部分组成：

- main.py：基础流程（模块级、非扩展 (2,2)-VCS）
- advanced_schemes.py：三种论文风格方案（Scheme I / II / III）

---

## 2. 代码文件结构（以当前仓库为准）

```text
sfrz1/
├── main.py
├── advanced_schemes.py
├── verify_success.py
├── requirements.txt
├── Basic_Output/
├── Scheme1_BVC/
├── Scheme2_OneMeaningful/
└── Scheme3_TwoMeaningful/
```

说明：

- verify_success.py 是验证脚本。
- README 里所有流程都与 main.py 和 advanced_schemes.py 当前实现保持一致。

---

## 3. 统一数据表示（理解算法最关键）

项目内部统一用“模块矩阵（module matrix）”做计算：

- 1 表示黑模块（black）
- 0 表示白模块（white）

可视化成图片时才做映射：

- black(1) -> 像素 0
- white(0) -> 像素 255

叠加规则采用黑色主导（按位 OR）：

- stack(a, b) = a OR b

因此：

- 只要任一份额该模块为黑（1），叠加就是黑。
- 只有两者都白（0），叠加才是白。

这个规则直接决定了所有构造约束。

---

## 4. 数学原理：为什么能“单份额无意义 + 叠加可恢复”

### 4.1 非扩展 (2,2)-VCS 模块级构造

对秘密模块 S(i,j)：

- 若 S = 0（白）：
  - 令 share1 = 0, share2 = 0
  - 叠加 0 OR 0 = 0（白）

- 若 S = 1（黑）：
  - 随机在 (1,0) 或 (0,1) 里选一个分配给两份额
  - 叠加 1 OR 0 = 1（黑）

结论：

- 两份额叠加后严格恢复秘密模块。
- 单份额仅看到随机黑白分布，不能直接恢复秘密。

### 4.2 高级方案中的“融合约束”

在高级方案里，q3 和 q4 既要看起来像目标载体/背景，又要满足：

- q3 OR q4 = secret

这在代码中由 _fuse_with_targets_under_secret_constraint(...) 实现。

其本质是一个受约束选择问题：

- 若 secret=0，只能选 (0,0)
- 若 secret=1，可选 (1,0)/(0,1)/(1,1)

然后从可行解里选最接近目标模块 target1/target2 的组合。

---

## 5. main.py：基础方案完整计算流程

入口：main()

### Step A：生成秘密二维码模块

- 函数：generate_secret_qr()
- 实际调用：_generate_qr_modules(data)
- 输出：secret_qr（0/1 模块矩阵）

### Step B：模块级分影

- 函数：encrypt_shares(secret_qr)
- 对每个模块执行非扩展 (2,2)-VCS 规则，得到 share1, share2

### Step C：份额叠加

- 函数：combine_shares(share1, share2)
- 计算：stacked = share1 OR share2

### Step D：恢复与扫码

- 函数：decrypt_qr(stacked)
- 非扩展方案无需块降采样，直接返回模块矩阵
- 函数：authenticate(restored)
  - 把模块矩阵转图片
  - 调 pyzbar 解码
  - 与原 token 比较

### Step E：保存输出

输出到 Basic_Output：

- 1_Original_Secret_QR.png
- 2_Share1_Server.png
- 3_Share2_Mobile.png
- 4_Stacked_Combined.png
- 5_Restored_QR.png

---

## 6. advanced_schemes.py：三方案详解

该文件核心思想是：

- 先得到 secret（秘密模块矩阵）
- 再根据方案生成/融合两个结果二维码 q3、q4
- 最后 stack(q3,q4) 恢复 secret

### 6.1 Scheme I（scheme_1_bvc）

论文关键词：

- 非扩展模块级分影
- 与载体 QR 融合

实现流程：

1. 生成 secret 和 carrier。
2. _generate_non_expansion_shadows(secret) 得到 s1,s2。
3. 构造融合目标：
   - t1 = carrier XOR s1
   - t2 = carrier XOR s2
4. 在约束 q3 OR q4 = secret 下，最小化与 t1,t2 的差异，求得 q3,q4。

说明：

- 代码采用“模块翻转约束优化”近似论文 RS/XOR 机制。
- 保留了“分影 + 融合 + 叠加恢复”的结构。

### 6.2 Scheme II（scheme_2_one_meaningful）

论文关键词：

- 两级融合
  - 阴影 -> 二值背景
  - 背景结果 -> 载体 QR

实现流程：

1. 生成 secret、carrier。
2. 非扩展分影得 s1,s2。
3. 生成两张二值背景 bg1,bg2。
4. 第一级融合：
   - fused_bg1 = bg1 XOR s1
   - fused_bg2 = bg2 XOR s2
5. 第二级融合目标：
   - t1 = carrier XOR fused_bg1
   - t2 = carrier XOR fused_bg2
6. 约束优化得到 q3,q4（保证 OR 后恢复 secret）。

效果：

- 相比 Scheme I，外观更像“背景 + 载体”的混合结果，隐蔽性更高。

### 6.3 Scheme III（scheme_3_two_meaningful）

论文关键词：

- ROI（感兴趣区域）
- 显著性（saliency）
- 纠错预算（error-correction budget）

实现流程：

1. 生成 secret、双载体 carrier_a/carrier_b。
2. 分影得到 s1,s2。
3. 构造彩色背景 color_bg，并转灰度后二值化成 bg_bin。
4. 设定 ROI（中间区域）。
5. 在 ROI 内把阴影注入背景：
   - bg1[ROI] = s1[ROI]
   - bg2[ROI] = s2[ROI]
6. 计算显著性图 _grayscale_saliency(color_bg)。
7. 构造功能区掩码 _functional_mask_like_qr，避免改动 finder/timing 近似区域。
8. 在 ROI 且非功能区里，按显著性由低到高选可改模块（不显眼优先）。
9. 设置预算 budget = 0.30 * 总模块数（近似 H 级纠错容量）。
10. 构造目标：
    - t1 = carrier_a XOR bg1
    - t2 = carrier_b XOR bg2
11. 在 candidate_mask + budget 限制下求 q3,q4，且满足 q3 OR q4 = secret。

效果：

- 相比 Scheme II，背景多样性更高（灰度/彩色场景），隐蔽性更强。

---

## 7. stack_and_decode 的统一恢复逻辑

函数：stack_and_decode(share1_black, share2_black, scale_factor)

流程：

1. stacked = share1 OR share2
2. 若 scale_factor > 1，可做块级降采样（兼容旧接口）
3. 把 restored 转图片后扫码解码
4. 返回 stacked_img, restored_img, token

当前 advanced_schemes.py 调用时 scale_factor=1（非扩展模块方案）。

---

## 8. 输出文件语义（高级方案目录）

每个方案目录（Scheme1_BVC / Scheme2_OneMeaningful / Scheme3_TwoMeaningful）包含：

- 0_Original_Secret_QR.png：原始秘密 QR
- 1_Share1_Server.png：第一张融合/份额二维码
- 2_Share2_Mobile.png：第二张融合/份额二维码
- 3_Stacked_Combined.png：两者叠加结果
- 4_Restored_Secret_QR.png：恢复后的可扫码秘密 QR

---

## 9. 如何运行

安装依赖：

```bash
pip install -r requirements.txt
```

运行基础流程：

```bash
python main.py
```

运行三种高级方案：

```bash
python advanced_schemes.py
```

验证输出是否可解码：

```bash
python verify_success.py
```

---

## 10. 关键函数与职责速查

main.py：

- _generate_qr_modules：生成 0/1 模块矩阵
- encrypt_shares：非扩展分影
- combine_shares：OR 叠加
- authenticate：扫码并比对 token

advanced_schemes.py：

- _generate_non_expansion_shadows：模块级分影
- _fuse_with_targets_under_secret_constraint：融合约束求解器
- _binary_background / _color_background：背景生成
- _grayscale_saliency：显著性估计
- _functional_mask_like_qr：功能区保护
- scheme_1_bvc / scheme_2_one_meaningful / scheme_3_two_meaningful：三方案主流程

---

## 11. 与论文的一致性说明（工程近似）

本实现与论文在“流程结构”上保持一致：

1. VCS 分影
2. 阴影融合（载体/背景）
3. 叠加恢复与扫码认证

在以下点采用工程近似：

- 论文的 RS/PBVM 细节未逐位编码实现；改为“模块翻转约束 + 预算”近似。
- ROI/saliency 使用轻量实现（梯度显著性 + 功能区掩码）。

这样做的好处：

- 更容易读懂和调试。
- 能稳定跑通并得到可扫码结果。
- 仍体现三方案从基础到高隐蔽性的演进逻辑。

---

## 12. 实验建议

如果你要做进一步实验，对结果影响最大的参数是：

- QR 版本与纠错级别（当前 H）
- ROI 大小与位置
- 预算比例（当前 30%）
- 显著性阈值策略
- 载体 QR 内容复杂度

建议按以下顺序调参：

1. 先固定 secret 与 carrier，只改 budget。
2. 再改 ROI 面积。
3. 最后改显著性筛选策略。

每次改动后都用 verify_success.py 检查解码成功率。

---

## 13. 一句话总结

这套代码的核心是：

- 用 OR 可恢复约束保证“安全恢复”，
- 用目标逼近（载体/背景/ROI/saliency/budget）提升“视觉隐蔽性”，
- 形成从基础 VC 到论文风格高级融合的完整可运行链路。
