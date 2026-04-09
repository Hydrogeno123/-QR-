import os
import random
from typing import List, Tuple

import numpy as np
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode


class VcQrSchemes:
    """
    论文思路对应实现（工程化近似）：
    - Scheme I: 非扩展(2,2)-VCS（模块级）+ 载体融合
    - Scheme II: 阴影→二值背景 融合，再与载体融合（两级融合）
    - Scheme III: ROI + 显著性 + 纠错预算约束下的融合

    说明：论文中的 RS/PBVM 细节较复杂，这里采用“模块翻转约束 + 预算控制”近似，
    但保持了三种方案的核心流程与结构差异。
    """

    def __init__(self, secret_data: str = "SECRET-AUTH-12345", size: int = 200):
        self.secret_data = secret_data
        self.size = size

    # ---------------------------
    # QR helpers
    # ---------------------------
    def _generate_qr_modules(self, data: str, version: int = 2, border: int = 4) -> np.ndarray:
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        # True 表示黑模块
        mat = np.array(qr.get_matrix(), dtype=np.uint8)
        return mat

    def _modules_to_image(self, modules_black: np.ndarray) -> np.ndarray:
        # black(1) -> 0, white(0) -> 255
        img = np.where(modules_black == 1, 0, 255).astype(np.uint8)
        img = np.array(Image.fromarray(img).resize((self.size, self.size), Image.NEAREST), dtype=np.uint8)
        return img

    def _decode_modules(self, modules_black: np.ndarray) -> str:
        img = self._modules_to_image(modules_black)
        decoded = decode(Image.fromarray(img))
        if decoded:
            return decoded[0].data.decode("utf-8")
        return None

    # ---------------------------
    # Core VC / fusion primitives
    # ---------------------------
    def _generate_non_expansion_shadows(self, secret_black: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Scheme I 使用的非扩展(2,2)-VCS（模块级）:
        - 白模块(0): 两阴影都置白(0)
        - 黑模块(1): 两阴影互补(1,0)/(0,1)
        """
        h, w = secret_black.shape
        s1 = np.zeros((h, w), dtype=np.uint8)
        s2 = np.zeros((h, w), dtype=np.uint8)

        for i in range(h):
            for j in range(w):
                if secret_black[i, j] == 0:
                    s1[i, j] = 0
                    s2[i, j] = 0
                else:
                    bit = random.randint(0, 1)
                    s1[i, j] = bit
                    s2[i, j] = 1 - bit

        return s1, s2

    def _stack_or(self, a_black: np.ndarray, b_black: np.ndarray) -> np.ndarray:
        # 叠加时黑色主导
        return np.bitwise_or(a_black, b_black)

    def _fuse_with_targets_under_secret_constraint(
        self,
        secret_black: np.ndarray,
        target1_black: np.ndarray,
        target2_black: np.ndarray,
        candidate_mask: np.ndarray = None,
        budget: int = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        在满足 stack(q3, q4) == secret 的前提下，
        让 q3/q4 尽量接近 target1/target2（用于近似论文的 XOR/纠错融合思想）。

        可通过 candidate_mask + budget 控制允许修改的位置数量（对应纠错能力预算）。
        """
        h, w = secret_black.shape
        q3 = np.zeros((h, w), dtype=np.uint8)
        q4 = np.zeros((h, w), dtype=np.uint8)

        if candidate_mask is None:
            candidate_mask = np.ones((h, w), dtype=bool)
        if budget is None:
            budget = h * w

        # 先默认全部可改，后续按预算冻结一部分到 target
        mutable_positions = [(i, j) for i in range(h) for j in range(w) if candidate_mask[i, j]]
        if len(mutable_positions) > budget:
            mutable_set = set(random.sample(mutable_positions, budget))
        else:
            mutable_set = set(mutable_positions)

        for i in range(h):
            for j in range(w):
                s = int(secret_black[i, j])
                t1 = int(target1_black[i, j])
                t2 = int(target2_black[i, j])

                if (i, j) not in mutable_set:
                    # 不允许改动：尽量贴近 target，同时保持叠加约束
                    if s == 0:
                        q3[i, j], q4[i, j] = 0, 0
                    else:
                        # 只能从可行解中选最接近 target
                        candidates = [(1, 0), (0, 1), (1, 1)]
                        q3[i, j], q4[i, j] = min(
                            candidates,
                            key=lambda p: abs(p[0] - t1) + abs(p[1] - t2),
                        )
                    continue

                if s == 0:
                    # 叠加为白必须 (0,0)
                    q3[i, j], q4[i, j] = 0, 0
                else:
                    # 叠加为黑可选 (1,0)/(0,1)/(1,1)
                    candidates = [(1, 0), (0, 1), (1, 1)]
                    q3[i, j], q4[i, j] = min(
                        candidates,
                        key=lambda p: abs(p[0] - t1) + abs(p[1] - t2),
                    )

        return q3, q4

    def _binary_background(self, shape: Tuple[int, int], seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        # 二值背景，带少量块状结构
        h, w = shape
        base = (rng.random((h, w)) > 0.5).astype(np.uint8)
        for _ in range(8):
            x0 = rng.integers(0, max(1, h - 4))
            y0 = rng.integers(0, max(1, w - 4))
            x1 = min(h, x0 + rng.integers(2, 6))
            y1 = min(w, y0 + rng.integers(2, 6))
            base[x0:x1, y0:y1] = rng.integers(0, 2)
        return base

    def _color_background(self, shape: Tuple[int, int], seed: int = 7) -> np.ndarray:
        rng = np.random.default_rng(seed)
        h, w = shape
        x = np.linspace(0, 1, w)
        y = np.linspace(0, 1, h)
        xv, yv = np.meshgrid(x, y)
        img = np.zeros((h, w, 3), dtype=np.float32)
        img[..., 0] = 0.65 * xv + 0.35 * rng.random((h, w))
        img[..., 1] = 0.55 * yv + 0.45 * rng.random((h, w))
        img[..., 2] = 0.35 * (1 - xv) + 0.65 * rng.random((h, w))
        img = np.clip(img, 0, 1)
        return (img * 255).astype(np.uint8)

    def _grayscale_saliency(self, color_bg: np.ndarray) -> np.ndarray:
        gray = 0.299 * color_bg[..., 0] + 0.587 * color_bg[..., 1] + 0.114 * color_bg[..., 2]
        gx = np.zeros_like(gray)
        gy = np.zeros_like(gray)
        gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
        gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
        sal = np.sqrt(gx * gx + gy * gy)
        if sal.max() > 0:
            sal = sal / sal.max()
        return sal

    def _functional_mask_like_qr(self, n: int) -> np.ndarray:
        """版本固定时的近似功能区掩码（避免改动这些区域）。"""
        mask = np.ones((n, n), dtype=bool)

        def block(x0: int, y0: int, sz: int = 9):
            x1 = min(n, x0 + sz)
            y1 = min(n, y0 + sz)
            mask[x0:x1, y0:y1] = False

        # 三个 finder + 分隔区近似
        block(0, 0)
        block(0, n - 9)
        block(n - 9, 0)

        # timing pattern 近似
        if n > 12:
            mask[6, :] = False
            mask[:, 6] = False

        return mask

    # ==========================================
    # Scheme 1: 非扩展模块级 + 载体融合
    # ==========================================
    def scheme_1_bvc(self, cover_data: str = "CARRIER-QR-S1"):
        print("\n--- Scheme 1: Non-expansion VCS + Carrier Fusion ---")
        secret = self._generate_qr_modules(self.secret_data, version=2, border=4)
        carrier = self._generate_qr_modules(cover_data, version=2, border=4)

        # (1) 生成非扩展阴影
        s1, s2 = self._generate_non_expansion_shadows(secret)

        # (2) 近似 XOR 融合思想：先把阴影映射到 carrier 目标域
        t1 = np.bitwise_xor(carrier, s1)
        t2 = np.bitwise_xor(carrier, s2)

        # (3) 在 stack 约束下优化得到两张美学二维码
        q3, q4 = self._fuse_with_targets_under_secret_constraint(secret, t1, t2)

        return q3, q4, secret

    # ==========================================
    # Scheme 2: 二值背景两级融合 + 载体融合
    # ==========================================
    def scheme_2_one_meaningful(self, cover_data: str = "CARRIER-QR-S2"):
        print("\n--- Scheme 2: Binary Background Two-level Fusion ---")
        secret = self._generate_qr_modules(self.secret_data, version=2, border=4)
        carrier = self._generate_qr_modules(cover_data, version=2, border=4)

        # Step 1: 阴影（非扩展，保持尺寸一致）
        s1, s2 = self._generate_non_expansion_shadows(secret)

        # Step 2: 阴影 -> 二值背景（第一层融合）
        bg1 = self._binary_background(secret.shape, seed=11)
        bg2 = self._binary_background(secret.shape, seed=23)
        fused_bg1 = np.bitwise_xor(bg1, s1)
        fused_bg2 = np.bitwise_xor(bg2, s2)

        # Step 3: 与载体二维码做第二层融合（XOR 思想近似）
        t1 = np.bitwise_xor(carrier, fused_bg1)
        t2 = np.bitwise_xor(carrier, fused_bg2)

        q3, q4 = self._fuse_with_targets_under_secret_constraint(secret, t1, t2)

        return q3, q4, secret

    # ==========================================
    # Scheme 3: ROI + 显著性 + 纠错预算融合
    # ==========================================
    def scheme_3_two_meaningful(self, cover_data_A: str = "CARRIER-A", cover_data_B: str = "CARRIER-B"):
        print("\n--- Scheme 3: ROI/Saliency/Error-Correction Guided Fusion ---")
        secret = self._generate_qr_modules(self.secret_data, version=2, border=4)
        carrier_a = self._generate_qr_modules(cover_data_A, version=2, border=4)
        carrier_b = self._generate_qr_modules(cover_data_B, version=2, border=4)

        # Step 1: 传统(2,2)-VCS 在论文中使用，这里做模块级近似。
        s1, s2 = self._generate_non_expansion_shadows(secret)

        # Step 2: 颜色背景 + ROI 替换
        color_bg = self._color_background(secret.shape, seed=37)
        gray = (0.299 * color_bg[..., 0] + 0.587 * color_bg[..., 1] + 0.114 * color_bg[..., 2]).astype(np.uint8)
        bg_bin = (gray < 128).astype(np.uint8)

        h, w = secret.shape
        roi = np.zeros((h, w), dtype=bool)
        x0, x1 = h // 5, h - h // 5
        y0, y1 = w // 5, w - w // 5
        roi[x0:x1, y0:y1] = True

        # ROI 中先注入阴影
        bg1 = bg_bin.copy()
        bg2 = bg_bin.copy()
        bg1[roi] = s1[roi]
        bg2[roi] = s2[roi]

        # Step 3: saliency + module layout 选可修改区域
        sal = self._grayscale_saliency(color_bg)
        functional_mask = self._functional_mask_like_qr(h)
        candidate = roi & functional_mask

        # 纠错预算：H 级约 30%，只在候选区域内消耗预算
        total_modules = int(h * w)
        budget = int(0.30 * total_modules)

        # 在候选里按显著性从低到高排序，优先改不显眼区域
        idx = np.argwhere(candidate)
        if len(idx) > 0:
            scores = sal[idx[:, 0], idx[:, 1]]
            order = np.argsort(scores)
            selected = idx[order[: min(budget, len(order))]]
            candidate_budget_mask = np.zeros_like(candidate)
            candidate_budget_mask[selected[:, 0], selected[:, 1]] = True
        else:
            candidate_budget_mask = np.zeros_like(candidate)

        # 目标：把背景注入后的结果再融合到双载体中
        t1 = np.bitwise_xor(carrier_a, bg1)
        t2 = np.bitwise_xor(carrier_b, bg2)

        q3, q4 = self._fuse_with_targets_under_secret_constraint(
            secret,
            t1,
            t2,
            candidate_mask=candidate_budget_mask,
            budget=budget,
        )

        return q3, q4, secret

    def stack_and_decode(self, share1_black: np.ndarray, share2_black: np.ndarray, scale_factor: int = 1):
        stacked = self._stack_or(share1_black, share2_black)

        if scale_factor > 1:
            # 兼容旧接口：若传入>1，执行降采样（多数情况下本实现不需要）
            h, w = stacked.shape
            restored = np.zeros((h // scale_factor, w // scale_factor), dtype=np.uint8)
            for i in range(0, h, scale_factor):
                for j in range(0, w, scale_factor):
                    block = stacked[i:i + scale_factor, j:j + scale_factor]
                    restored[i // scale_factor, j // scale_factor] = 1 if np.any(block == 1) else 0
        else:
            restored = stacked

        token = self._decode_modules(restored)
        stacked_img = self._modules_to_image(stacked)
        restored_img = self._modules_to_image(restored)
        return stacked_img, restored_img, token


def save_and_verify(scheme_name: str, s1_black: np.ndarray, s2_black: np.ndarray, sec_black: np.ndarray, scale_factor: int, auth: VcQrSchemes):
    os.makedirs(scheme_name, exist_ok=True)

    Image.fromarray(auth._modules_to_image(sec_black)).save(f"{scheme_name}/0_Original_Secret_QR.png")
    Image.fromarray(auth._modules_to_image(s1_black)).save(f"{scheme_name}/1_Share1_Server.png")
    Image.fromarray(auth._modules_to_image(s2_black)).save(f"{scheme_name}/2_Share2_Mobile.png")

    stacked_img, restored_img, token = auth.stack_and_decode(s1_black, s2_black, scale_factor=scale_factor)
    Image.fromarray(stacked_img).save(f"{scheme_name}/3_Stacked_Combined.png")
    Image.fromarray(restored_img).save(f"{scheme_name}/4_Restored_Secret_QR.png")

    print(f"[*] Saved to folder '{scheme_name}'")
    if token == auth.secret_data:
        print(f"[+] SUCCESS! Decoded Token: {token}")
    else:
        print(f"[-] FAILED! Could not decode correctly.")


if __name__ == "__main__":
    auth = VcQrSchemes(secret_data="SECURE-PAY-12345", size=100)

    # Scheme 1
    s1_1, s2_1, sec1 = auth.scheme_1_bvc()
    save_and_verify("Scheme1_BVC", s1_1, s2_1, sec1, 1, auth)

    # Scheme 2
    s1_2, s2_2, sec2 = auth.scheme_2_one_meaningful(cover_data="PUBLIC-QR-STORE")
    save_and_verify("Scheme2_OneMeaningful", s1_2, s2_2, sec2, 1, auth)

    # Scheme 3
    s1_3, s2_3, sec3 = auth.scheme_3_two_meaningful(cover_data_A="ALICE-PUB", cover_data_B="STORE-B")
    save_and_verify("Scheme3_TwoMeaningful", s1_3, s2_3, sec3, 1, auth)
