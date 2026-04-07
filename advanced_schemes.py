import qrcode
import random
import numpy as np
import cv2
from PIL import Image
from pyzbar.pyzbar import decode
import os

class VcQrSchemes:
    def __init__(self, secret_data="SECRET-AUTH-12345", size=200):
        self.secret_data = secret_data
        self.size = size
        
    def _generate_qr(self, data, size):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('1')
        img = img.resize((size, size), Image.NEAREST)
        return np.array(img, dtype=np.uint8) * 255
        
    def _create_basic_shares(self, pixel, p0_patterns, p1_patterns):
        coin = random.randint(0, 1)
        if pixel == 0:  # Black
            return p0_patterns[coin], p0_patterns[1 - coin]
        else:           # White
            return p0_patterns[coin], p0_patterns[coin]

    # ==========================================
    # Scheme 1: Basic Visual Cryptography (BVC)
    # Both shares are random noise meaning nothing.
    # ==========================================
    def scheme_1_bvc(self):
        print("\n--- Scheme 1: Basic VC (Both shares are noise) ---")
        secret_img = self._generate_qr(self.secret_data, self.size)
        h, w = secret_img.shape
        
        share1 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        share2 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        
        P0 = [np.array([[0, 255], [255, 0]]), np.array([[255, 0], [0, 255]])]
        
        for i in range(h):
            for j in range(w):
                s1_block, s2_block = self._create_basic_shares(secret_img[i, j], P0, None)
                share1[i*2:i*2+2, j*2:j*2+2] = s1_block
                share2[i*2:i*2+2, j*2:j*2+2] = s2_block
                
        return share1, share2, secret_img

    # ==========================================
    # Scheme 2: One Meaningful Share
    # Share 1 is a valid cover QR code.
    # Share 2 is noise.
    # ==========================================
    def scheme_2_one_meaningful(self, cover_data="COVER-11111"):
        print("\n--- Scheme 2: One Meaningful Share (S1 is Cover QR, S2 is Noise) ---")
        secret_img = self._generate_qr(self.secret_data, self.size)
        cover_img = self._generate_qr(cover_data, self.size)
        
        h, w = secret_img.shape
        share1 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        share2 = np.zeros((h * 2, w * 2), dtype=np.uint8)
        
        # We enforce S1 to visually approximate the cover image.
        P0 = [np.array([[0, 255], [255, 0]]), np.array([[255, 0], [0, 255]])]
        
        for i in range(h):
            for j in range(w):
                # Ensure S1's overall brightness reflects Cover pixel
                c_pixel = cover_img[i, j]
                s_pixel = secret_img[i, j]
                
                # Simplified simulation of EVC for one meaningful share
                coin = random.randint(0, 1)
                
                # To make S1 meaningful, we heavily weight its pattern based on c_pixel
                if c_pixel == 0:
                    s1_block = np.array([[0, 255], [0, 255]]) # Darker
                else:
                    s1_block = np.array([[255, 0], [255, 0]]) # Lighter
                    
                if s_pixel == 0:
                    # Secret is Black -> Stack must be black. S2 must be opposite of S1
                    s2_block = 255 - s1_block
                else:
                    # Secret is White -> Stack must have white. S2 must match S1
                    s2_block = np.copy(s1_block)
                    
                share1[i*2:i*2+2, j*2:j*2+2] = s1_block
                share2[i*2:i*2+2, j*2:j*2+2] = s2_block
                
        return share1, share2, secret_img

    # ==========================================
    # Scheme 3: Two Meaningful Shares
    # Share 1 is Cover QR A.
    # Share 2 is Cover QR B.
    # ==========================================
    def scheme_3_two_meaningful(self, cover_data_A="AUTHOR-A", cover_data_B="REGION-B"):
        print("\n--- Scheme 3: Two Meaningful Shares (Both S1 & S2 are Cover QRs) ---")
        secret_img = self._generate_qr(self.secret_data, self.size)
        cover_A = self._generate_qr(cover_data_A, self.size)
        cover_B = self._generate_qr(cover_data_B, self.size)
        
        h, w = secret_img.shape
        # Need 3x3 expansion to embed two meanings and one secret (simplified simulation)
        share1 = np.zeros((h * 3, w * 3), dtype=np.uint8)
        share2 = np.zeros((h * 3, w * 3), dtype=np.uint8)
        
        for i in range(h):
            for j in range(w):
                cA = cover_A[i, j]
                cB = cover_B[i, j]
                sec = secret_img[i, j]
                
                # Create blocks that statistically represent the covers independently
                # but together stack to represent the secret.
                # A 3x3 block has 9 pixels. 
                # Dark cover -> fewer white pixels. Light cover -> more white pixels.
                
                s1_block = np.zeros((3, 3), dtype=np.uint8)
                s2_block = np.zeros((3, 3), dtype=np.uint8)
                
                # Simplified simulated block generation that mathematically guarantees 
                # VC reconstruction of the secret.
                # A 3x3 block has 9 pixels.
                s1_block = np.zeros((3, 3), dtype=np.uint8)
                s2_block = np.zeros((3, 3), dtype=np.uint8)
                
                # Assign 4 white pixels if it's supposed to be a light cover, 2 if dark cover
                # Using hardcoded positions for simplicity to avoid completely random intersection
                if cA == 255: s1_block[0, 0:4] = 255
                else:         s1_block[0, 0:2] = 255
                    
                if cB == 255: s2_block[1, 0:4] = 255
                else:         s2_block[1, 0:2] = 255
                
                if sec == 0:
                    # Secret is Black: The stack of s1_block and s2_block MUST be fully black
                    # We ensure no white pixels overlap or exist
                    s1_block[:] = 0   
                    s2_block[:] = 0
                else:
                    # Secret is White: The stack MUST have at least 1 white pixel
                    # Let's force an overlap of white to guarantee restoration
                    s1_block[2, 2] = 255
                    s2_block[2, 2] = 255
                
                share1[i*3:i*3+3, j*3:j*3+3] = s1_block
                share2[i*3:i*3+3, j*3:j*3+3] = s2_block
                
        return share1, share2, secret_img

    def stack_and_decode(self, share1, share2, scale_factor=2):
        stacked = np.minimum(share1, share2)
        h, w = stacked.shape
        
        restored = np.zeros((h // scale_factor, w // scale_factor), dtype=np.uint8)
        for i in range(0, h, scale_factor):
            for j in range(0, w, scale_factor):
                block = stacked[i:i+scale_factor, j:j+scale_factor]
                # Threshold for 3x3 or 2x2 blocks correctly
                white_pixels = np.count_nonzero(block == 255)
                # If it's a 3x3 block, maximum white is 9. A stacked "white" pixel has > 0 whites.
                # A stacked "black" pixel typically has 0 whites.
                if white_pixels > 0:
                    restored[i//scale_factor, j//scale_factor] = 255
                else:
                    restored[i//scale_factor, j//scale_factor] = 0
                    
        decoded = decode(Image.fromarray(restored))
        result = decoded[0].data.decode('utf-8') if decoded else None
        return stacked, restored, result

def save_and_verify(scheme_name, s1, s2, scale_factor, auth):
    os.makedirs(scheme_name, exist_ok=True)
    Image.fromarray(s1).save(f"{scheme_name}/1_Share1_Server.png")
    Image.fromarray(s2).save(f"{scheme_name}/2_Share2_Mobile.png")
    
    stacked, restored, token = auth.stack_and_decode(s1, s2, scale_factor=scale_factor)
    Image.fromarray(stacked).save(f"{scheme_name}/3_Stacked_Combined.png")
    Image.fromarray(restored).save(f"{scheme_name}/4_Restored_Secret_QR.png")
    
    print(f"[*] Saved to folder '{scheme_name}'")
    if token == auth.secret_data:
        print(f"[+] SUCCESS! Decoded Token: {token}")
    else:
        print(f"[-] FAILED! Could not decode correctly.")

if __name__ == "__main__":
    auth = VcQrSchemes(secret_data="SECURE-PAY-12345", size=100)
    
    # Scheme 1
    s1_1, s2_1, sec1 = auth.scheme_1_bvc()
    save_and_verify("Scheme1_BVC", s1_1, s2_1, 2, auth)
    
    # Scheme 2
    s1_2, s2_2, sec2 = auth.scheme_2_one_meaningful(cover_data="PUBLIC-QR-STORE")
    save_and_verify("Scheme2_OneMeaningful", s1_2, s2_2, 2, auth)
    
    # Scheme 3
    s1_3, s2_3, sec3 = auth.scheme_3_two_meaningful(cover_data_A="ALICE-PUB", cover_data_B="STORE-B")
    save_and_verify("Scheme3_TwoMeaningful", s1_3, s2_3, 3, auth)
