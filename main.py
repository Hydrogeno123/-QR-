import os
import random

import numpy as np
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode


class VcQrAuthenticator:
    """
    基础脚本改为模块级非扩展(2,2)-VCS。
    与论文 Scheme I 的“非扩展模块分影”核心思路保持一致。
    """

    def __init__(self, data: str = "Auth-Data-12345", size: int = 256):
        self.data = data
        self.size = size

    def _generate_qr_modules(self, data: str, version: int = 2, border: int = 4) -> np.ndarray:
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return np.array(qr.get_matrix(), dtype=np.uint8)  # 1=black, 0=white

    def _modules_to_image(self, modules_black: np.ndarray) -> np.ndarray:
        img = np.where(modules_black == 1, 0, 255).astype(np.uint8)
        img = np.array(Image.fromarray(img).resize((self.size, self.size), Image.NEAREST), dtype=np.uint8)
        return img

    def generate_secret_qr(self):
        return self._generate_qr_modules(self.data)

    def encrypt_shares(self, secret_modules):
        h, w = secret_modules.shape
        share1 = np.zeros((h, w), dtype=np.uint8)
        share2 = np.zeros((h, w), dtype=np.uint8)

        # 非扩展模块规则：
        # - 白模块: (0,0)
        # - 黑模块: (1,0)/(0,1)
        for i in range(h):
            for j in range(w):
                if secret_modules[i, j] == 0:
                    share1[i, j] = 0
                    share2[i, j] = 0
                else:
                    bit = random.randint(0, 1)
                    share1[i, j] = bit
                    share2[i, j] = 1 - bit

        return share1, share2

    def combine_shares(self, share1, share2):
        # 叠加黑色主导
        return np.bitwise_or(share1, share2)

    def decrypt_qr(self, combined_modules):
        # 非扩展方案无需 block 恢复
        return combined_modules

    def authenticate(self, restored_modules):
        img_pil = Image.fromarray(self._modules_to_image(restored_modules))
        decoded = decode(img_pil)
        if decoded:
            extracted = decoded[0].data.decode("utf-8")
            return extracted == self.data, extracted
        return False, None


def main():
    print("=== QR Code + Visual Cryptography Authentication System ===")

    output_dir = "Basic_Output"
    os.makedirs(output_dir, exist_ok=True)

    secret_token = "USER_AUTH_TOKEN_778899"
    auth = VcQrAuthenticator(data=secret_token, size=150)

    # 1. Generate secret QR (module matrix)
    secret_qr = auth.generate_secret_qr()
    Image.fromarray(auth._modules_to_image(secret_qr)).save(f"{output_dir}/1_Original_Secret_QR.png")
    print("[*] Generated Original Secret QR Code.")

    # 2. Split into two shares
    share1, share2 = auth.encrypt_shares(secret_qr)
    Image.fromarray(auth._modules_to_image(share1)).save(f"{output_dir}/2_Share1_Server.png")
    Image.fromarray(auth._modules_to_image(share2)).save(f"{output_dir}/3_Share2_Mobile.png")
    print("[*] Encrypted into Share 1 (Server) and Share 2 (Mobile App).")

    # 3. Stack shares
    stacked = auth.combine_shares(share1, share2)
    Image.fromarray(auth._modules_to_image(stacked)).save(f"{output_dir}/4_Stacked_Combined.png")
    print("[*] Combined Shares (Stacked).")

    # 4. Restore QR
    restored_qr = auth.decrypt_qr(stacked)
    Image.fromarray(auth._modules_to_image(restored_qr)).save(f"{output_dir}/5_Restored_QR.png")
    print("[*] Restored QR Code for Scanning.")

    # 5. Authenticate
    is_valid, decoded_token = auth.authenticate(restored_qr)
    if is_valid:
        print(f"[+] Authentication SUCCESSFUL! Token matched: {decoded_token}")
    else:
        print("[-] Authentication FAILED. Could not decode or string mismatched.")


if __name__ == "__main__":
    main()
