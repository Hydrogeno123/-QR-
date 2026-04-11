"""Verify that stacked shares decode to the correct token for all schemes."""

import os

import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode

TEST_TOKEN = "AUTH-2024-VC-DEMO"

SCHEMES = [
    ("Basic_Output", "2_Share1_Server.png", "3_Share2_Mobile.png"),
    ("Scheme1_BVC", "1_Share1_Server.png", "2_Share2_Mobile.png"),
    ("Scheme2_OneMeaningful", "1_Share1_Server.png", "2_Share2_Mobile.png"),
    ("Scheme3_TwoMeaningful", "1_Share1_Server.png", "2_Share2_Mobile.png"),
]


def _image_to_modules(img: Image.Image) -> np.ndarray:
    """Convert a grayscale PIL image back to a 0/1 module matrix.

    Threshold at 128: pixel < 128 -> black(1), else white(0).
    """
    pixels = np.array(img, dtype=np.uint8)
    return (pixels < 128).astype(np.int8)


def verify_directory(dir_name: str, share1_name: str, share2_name: str) -> bool:
    """Load two share images, stack them, and verify the decoded token."""
    s1_path = os.path.join(dir_name, share1_name)
    s2_path = os.path.join(dir_name, share2_name)

    if not os.path.exists(s1_path) or not os.path.exists(s2_path):
        print(f"  {dir_name}: FAIL (missing files)")
        return False

    s1_img = Image.open(s1_path).convert("L")
    s2_img = Image.open(s2_path).convert("L")

    # Ensure same size
    if s1_img.size != s2_img.size:
        s2_img = s2_img.resize(s1_img.size, Image.NEAREST)

    s1_mod = _image_to_modules(s1_img)
    s2_mod = _image_to_modules(s2_img)

    stacked = (s1_mod | s2_mod).astype(np.int8)

    # Convert stacked modules to image for decoding
    pixels = np.where(stacked == 1, 0, 255).astype(np.uint8)
    stacked_img = Image.fromarray(pixels, mode="L")

    results = decode(stacked_img)
    if not results:
        print(f"  {dir_name}: FAIL (no QR detected)")
        return False

    decoded = results[0].data.decode("utf-8")
    if decoded == TEST_TOKEN:
        print(f"  {dir_name}: PASS (decoded: {decoded})")
        return True
    else:
        print(f"  {dir_name}: FAIL (decoded: {decoded}, expected: {TEST_TOKEN})")
        return False


def main() -> None:
    print("Verifying all schemes...\n")

    results = []
    for dir_name, s1_name, s2_name in SCHEMES:
        ok = verify_directory(dir_name, s1_name, s2_name)
        results.append((dir_name, ok))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\nSummary: {passed}/{total} schemes passed")

    if passed == total:
        print("All verifications PASSED!")
    else:
        failed = [name for name, ok in results if not ok]
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
