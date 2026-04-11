"""Basic non-expansion (2,2)-VCS QR authentication flow."""

import os

import numpy as np
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

TEST_TOKEN = "AUTH-2024-VC-DEMO"


def _generate_qr_modules(data: str) -> np.ndarray:
    """Generate a 0/1 module matrix from input data using QR code version 3, error correction H."""
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=False)
    modules = np.array([[1 if m else 0 for m in row] for row in qr.modules], dtype=np.int8)
    return modules


def _modules_to_image(modules: np.ndarray, scale: int = 10) -> Image.Image:
    """Convert a 0/1 module matrix to a PIL grayscale image.

    Mapping: black(1) -> pixel 0, white(0) -> pixel 255.
    """
    pixels = np.where(modules == 1, 0, 255).astype(np.uint8)
    if scale > 1:
        pixels = np.repeat(np.repeat(pixels, scale, axis=0), scale, axis=1)
    return Image.fromarray(pixels, mode="L")


def generate_secret_qr() -> np.ndarray:
    """Generate the secret QR module matrix from TEST_TOKEN."""
    return _generate_qr_modules(TEST_TOKEN)


def encrypt_shares(secret_qr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split secret into two shares using non-expansion (2,2)-VCS.

    White(0) -> (0,0).  Black(1) -> randomly (1,0) or (0,1).
    """
    h, w = secret_qr.shape
    share1 = np.zeros_like(secret_qr)
    share2 = np.zeros_like(secret_qr)

    black_mask = secret_qr == 1
    n_black = black_mask.sum()
    random_bits = np.random.randint(0, 2, size=n_black).astype(np.int8)

    rows, cols = np.where(black_mask)
    share1[rows, cols] = random_bits
    share2[rows, cols] = 1 - random_bits

    return share1, share2


def combine_shares(s1: np.ndarray, s2: np.ndarray) -> np.ndarray:
    """Stack two shares using OR to recover the secret."""
    return (s1 | s2).astype(np.int8)


def decrypt_qr(stacked: np.ndarray) -> np.ndarray:
    """Return the stacked module matrix (identity for non-expansion scheme)."""
    return stacked


def authenticate(restored: np.ndarray, expected_token: str) -> bool:
    """Decode the restored QR and compare with the expected token."""
    img = _modules_to_image(restored, scale=10)
    results = decode(img)
    if not results:
        print("Authentication: FAILED (no QR code detected)")
        return False
    decoded = results[0].data.decode("utf-8")
    if decoded == expected_token:
        print(f"Authentication: SUCCESS (decoded: {decoded})")
        return True
    else:
        print(f"Authentication: FAILED (decoded: {decoded}, expected: {expected_token})")
        return False


def main() -> None:
    np.random.seed(42)
    os.makedirs("Basic_Output", exist_ok=True)

    # Step A: generate secret QR
    secret = generate_secret_qr()
    print(f"Secret QR shape: {secret.shape}")

    # Step B: split into shares
    s1, s2 = encrypt_shares(secret)

    # Step C: combine shares
    stacked = combine_shares(s1, s2)

    # Step D: decrypt & authenticate
    restored = decrypt_qr(stacked)
    ok = authenticate(restored, TEST_TOKEN)

    # Step E: save outputs
    _modules_to_image(secret).save("Basic_Output/1_Original_Secret_QR.png")
    _modules_to_image(s1).save("Basic_Output/2_Share1_Server.png")
    _modules_to_image(s2).save("Basic_Output/3_Share2_Mobile.png")
    _modules_to_image(stacked).save("Basic_Output/4_Stacked_Combined.png")
    _modules_to_image(restored).save("Basic_Output/5_Restored_QR.png")

    perfect = np.array_equal(secret, restored)
    print(f"Perfect recovery: {perfect}")
    print(f"Results saved to Basic_Output/")


if __name__ == "__main__":
    main()
