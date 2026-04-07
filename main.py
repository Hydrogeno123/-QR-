import qrcode
import random
import numpy as np
import cv2
from PIL import Image
from pyzbar.pyzbar import decode
import os

class VcQrAuthenticator:
    def __init__(self, data="Auth-Data-12345", size=256):
        self.data = data
        self.size = size

    def generate_secret_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(self.data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('1')
        img = img.resize((self.size, self.size), Image.NEAREST)
        return np.array(img, dtype=np.uint8) * 255  # 0 for black, 255 for white

    def encrypt_shares(self, secret_image):
        h, w = secret_image.shape
        share1 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        share2 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        
        # Standard 2x2 Basic Visual Cryptography Scheme
        # Black pixel patterns
        P0 = [np.array([[0, 255], [255, 0]]), np.array([[255, 0], [0, 255]])]
        # White pixel patterns
        P1 = [np.array([[255, 0], [255, 0]]), np.array([[0, 255], [0, 255]])]
        
        for i in range(h):
            for j in range(w):
                pixel = secret_image[i, j]
                coin = random.randint(0, 1)
                
                if pixel == 0:  # Black pixel
                    share1[i*2:i*2+2, j*2:j*2+2] = P0[coin]
                    share2[i*2:i*2+2, j*2:j*2+2] = P0[1 - coin]
                else:  # White pixel
                    share1[i*2:i*2+2, j*2:j*2+2] = P0[coin]
                    share2[i*2:i*2+2, j*2:j*2+2] = P0[coin]
                    
        return share1, share2

    def combine_shares(self, share1, share2):
        # Stacking shares (simulate visual OR operation -> 0 is black, 255 is white)
        # 0 (B) AND 0 (B) = 0 (B)
        # 0 (B) AND 255 (W) = 0 (B)
        # 255 (W) AND 255 (W) = 255 (W)
        # We can use minimum for dark stacking or bitwise AND
        combined = np.minimum(share1, share2)
        return combined

    def decrypt_qr(self, combined_image):
        # To make it readable, we might need some thresholding or morphological operations
        # Since it's a 2x2 block, we can shrink it back to original resolution
        h, w = combined_image.shape
        restored = np.zeros((h//2, w//2), dtype=np.uint8)
        
        for i in range(0, h, 2):
            for j in range(0, w, 2):
                block = combined_image[i:i+2, j:j+2]
                # If there are any white pixels in the block, it was a white pixel originally
                # In standard VC, white original -> half white, half black. Black original -> all black
                if np.sum(block) > 0:
                    restored[i//2, j//2] = 255
                else:
                    restored[i//2, j//2] = 0
                    
        return restored

    def authenticate(self, restored_img):
        img_pil = Image.fromarray(restored_img)
        decoded = decode(img_pil)
        if decoded:
            extracted = decoded[0].data.decode('utf-8')
            if extracted == self.data:
                return True, extracted
            else:
                return False, extracted
        return False, None

def main():
    print("=== QR Code + Visual Cryptography Authentication System ===")
    
    # User's secret authentication token
    secret_token = "USER_AUTH_TOKEN_778899"
    auth = VcQrAuthenticator(data=secret_token, size=150)
    
    # 1. Generate the secret QR code
    secret_qr = auth.generate_secret_qr()
    Image.fromarray(secret_qr).save("1_secret_qr.png")
    print("[*] Generated Original Secret QR Code.")
    
    # 2. Split into two shares
    share1, share2 = auth.encrypt_shares(secret_qr)
    Image.fromarray(share1).save("2_share1_server.png")
    Image.fromarray(share2).save("3_share2_mobile.png")
    print("[*] Encrypted into Share 1 (Server) and Share 2 (Mobile App).")
    
    # 3. Simulate stacking the shares (e.g. scanning phone screen with a transparent overlay or digital composite)
    stacked = auth.combine_shares(share1, share2)
    Image.fromarray(stacked).save("4_stacked_combined.png")
    print("[*] Combined Shares (Stacked).")
    
    # 4. Restore the QR code from the stacked image for decoding
    restored_qr = auth.decrypt_qr(stacked)
    Image.fromarray(restored_qr).save("5_restored_qr.png")
    print("[*] Restored QR Code for Scanning.")
    
    # 5. Authenticate
    is_valid, decoded_token = auth.authenticate(restored_qr)
    if is_valid:
        print(f"[+] Authentication SUCCESSFUL! Token matched: {decoded_token}")
    else:
        print("[-] Authentication FAILED. Could not decode or string mismatched.")

if __name__ == '__main__':
    main()
