"""Three advanced visual-cryptography QR authentication schemes (BVC, OneMeaningful, TwoMeaningful)."""

import os

import numpy as np
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

TEST_TOKEN = "AUTH-2024-VC-DEMO"

# Carrier data must fit in QR version 3, error-correction H (max 35 bytes).
CARRIER_A = "https://example.com/a"
CARRIER_B = "https://example.com/b"


# ---------------------------------------------------------------------------
# Shared helpers (self-contained, same as main.py)
# ---------------------------------------------------------------------------

def _generate_qr_modules(data: str) -> np.ndarray:
    """Generate a 0/1 module matrix from input data."""
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=False)
    return np.array([[1 if m else 0 for m in row] for row in qr.modules], dtype=np.int8)


def _modules_to_image(modules: np.ndarray, scale: int = 10) -> Image.Image:
    """Convert 0/1 module matrix to grayscale PIL image.  1=black(0), 0=white(255)."""
    pixels = np.where(modules == 1, 0, 255).astype(np.uint8)
    if scale > 1:
        pixels = np.repeat(np.repeat(pixels, scale, axis=0), scale, axis=1)
    return Image.fromarray(pixels, mode="L")


def _save_scheme(out_dir: str, secret: np.ndarray, q3: np.ndarray, q4: np.ndarray) -> None:
    """Save the 5 standard output images for a scheme."""
    os.makedirs(out_dir, exist_ok=True)
    stacked = (q3 | q4).astype(np.int8)
    _modules_to_image(secret).save(f"{out_dir}/0_Original_Secret_QR.png")
    _modules_to_image(q3).save(f"{out_dir}/1_Share1_Server.png")
    _modules_to_image(q4).save(f"{out_dir}/2_Share2_Mobile.png")
    _modules_to_image(stacked).save(f"{out_dir}/3_Stacked_Combined.png")
    _modules_to_image(stacked).save(f"{out_dir}/4_Restored_Secret_QR.png")


# ---------------------------------------------------------------------------
# VCS
# ---------------------------------------------------------------------------

def _generate_non_expansion_shadows(secret: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Non-expansion (2,2)-VCS: white->(0,0), black->random(1,0) or (0,1)."""
    share1 = np.zeros_like(secret)
    share2 = np.zeros_like(secret)
    black_mask = secret == 1
    n_black = black_mask.sum()
    if n_black > 0:
        rand = np.random.randint(0, 2, size=n_black).astype(np.int8)
        rows, cols = np.where(black_mask)
        share1[rows, cols] = rand
        share2[rows, cols] = 1 - rand
    return share1, share2


# ---------------------------------------------------------------------------
# Core constraint solver
# ---------------------------------------------------------------------------

def _fuse_with_targets_under_secret_constraint(
    t1: np.ndarray, t2: np.ndarray, secret: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Find (q3, q4) such that q3 OR q4 == secret, minimizing distance to (t1, t2).

    secret=0 -> only (0,0).
    secret=1 -> pick from (1,0), (0,1), (1,1) closest to (t1,t2).
    """
    q3 = np.zeros_like(secret)
    q4 = np.zeros_like(secret)

    # Vectorized for secret==1 positions
    black_mask = secret == 1
    rows, cols = np.where(black_mask)
    if len(rows) == 0:
        return q3, q4

    t1v = t1[rows, cols].astype(np.float64)
    t2v = t2[rows, cols].astype(np.float64)

    # Three candidates: (1,0), (0,1), (1,1)
    dist_10 = (1 - t1v) ** 2 + (0 - t2v) ** 2
    dist_01 = (0 - t1v) ** 2 + (1 - t2v) ** 2
    dist_11 = (1 - t1v) ** 2 + (1 - t2v) ** 2

    dists = np.stack([dist_10, dist_01, dist_11], axis=1)  # (N, 3)
    best = np.argmin(dists, axis=1)  # 0, 1, or 2

    # Assign based on best candidate
    q3[rows, cols] = np.where(best == 2, 1, np.where(best == 0, 1, 0))
    q4[rows, cols] = np.where(best == 2, 1, np.where(best == 1, 1, 0))

    return q3, q4


# ---------------------------------------------------------------------------
# Background generators
# ---------------------------------------------------------------------------

def _binary_background(shape: tuple[int, ...], seed: int = 0) -> np.ndarray:
    """Generate a pseudo-random 0/1 background."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 2, size=shape).astype(np.int8)


def _color_background(shape: tuple[int, int], seed: int = 0) -> np.ndarray:
    """Generate a synthetic color background with smooth gradients."""
    rng = np.random.RandomState(seed)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    r = (128 + 127 * np.sin(xx / w * 2 * np.pi + rng.uniform(0, 2 * np.pi))).astype(np.uint8)
    g = (128 + 127 * np.sin(yy / h * 2 * np.pi + rng.uniform(0, 2 * np.pi))).astype(np.uint8)
    b = (128 + 127 * np.sin((xx + yy) / (w + h) * 2 * np.pi + rng.uniform(0, 2 * np.pi))).astype(np.uint8)
    return np.stack([r, g, b], axis=2)


# ---------------------------------------------------------------------------
# Saliency & functional mask
# ---------------------------------------------------------------------------

def _grayscale_saliency(color_bg: np.ndarray) -> np.ndarray:
    """Compute gradient-based saliency from a color background (H, W, 3)."""
    gray = (0.299 * color_bg[:, :, 0] + 0.587 * color_bg[:, :, 1] + 0.114 * color_bg[:, :, 2]).astype(np.float64)
    gx = np.gradient(gray, axis=1)
    gy = np.gradient(gray, axis=0)
    saliency = np.sqrt(gx ** 2 + gy ** 2)
    mx = saliency.max()
    if mx > 0:
        saliency /= mx
    return saliency


def _functional_mask_like_qr(shape: tuple[int, int]) -> np.ndarray:
    """Return boolean mask where True = protected (finder/timing/alignment regions)."""
    h, w = shape
    mask = np.zeros(shape, dtype=bool)

    # Finder patterns + separators (8x8 each corner)
    mask[0:8, 0:8] = True          # top-left
    mask[0:8, w - 8:w] = True      # top-right
    mask[h - 8:h, 0:8] = True      # bottom-left

    # Timing patterns
    if h > 16 and w > 16:
        mask[6, 8:w - 8] = True     # horizontal
        mask[8:h - 8, 6] = True     # vertical

    # Alignment pattern for version 3 (centered at 22,22)
    if h >= 25 and w >= 25:
        mask[20:25, 20:25] = True

    return mask


# ---------------------------------------------------------------------------
# Decode helper
# ---------------------------------------------------------------------------

def stack_and_decode(
    share1_black: np.ndarray, share2_black: np.ndarray, scale_factor: int = 1
) -> tuple[Image.Image, Image.Image, str | None]:
    """Stack two shares, decode the result.

    Returns (stacked_pil, restored_pil, token_or_None).
    """
    stacked = (share1_black | share2_black).astype(np.int8)
    stacked_img = _modules_to_image(stacked, scale=10)
    restored_img = stacked_img  # identity for non-expansion

    results = decode(stacked_img)
    token = results[0].data.decode("utf-8") if results else None
    return stacked_img, restored_img, token


# ---------------------------------------------------------------------------
# Scheme I: BVC (carrier QR fusion)
# ---------------------------------------------------------------------------

def scheme_1_bvc() -> None:
    """Scheme I: non-expansion shadows fused with a carrier QR."""
    np.random.seed(42)
    print("=== Scheme I: BVC ===")

    secret = _generate_qr_modules(TEST_TOKEN)
    carrier = _generate_qr_modules(CARRIER_A)

    s1, s2 = _generate_non_expansion_shadows(secret)

    t1 = (carrier ^ s1).astype(np.int8)
    t2 = (carrier ^ s2).astype(np.int8)

    q3, q4 = _fuse_with_targets_under_secret_constraint(t1, t2, secret)

    assert np.array_equal(q3 | q4, secret), "Scheme I: OR constraint violated!"

    _save_scheme("Scheme1_BVC", secret, q3, q4)

    _, _, token = stack_and_decode(q3, q4)
    status = "SUCCESS" if token == TEST_TOKEN else f"FAILED (got {token})"
    print(f"  Decode: {status}")


# ---------------------------------------------------------------------------
# Scheme II: One-Meaningful (two-level XOR chain)
# ---------------------------------------------------------------------------

def scheme_2_one_meaningful() -> None:
    """Scheme II: two-level fusion with binary backgrounds and carrier QR."""
    np.random.seed(42)
    print("=== Scheme II: One-Meaningful ===")

    secret = _generate_qr_modules(TEST_TOKEN)
    carrier = _generate_qr_modules(CARRIER_A)

    s1, s2 = _generate_non_expansion_shadows(secret)

    bg1 = _binary_background(secret.shape, seed=42)
    bg2 = _binary_background(secret.shape, seed=99)

    # First-level fusion
    fused_bg1 = (bg1 ^ s1).astype(np.int8)
    fused_bg2 = (bg2 ^ s2).astype(np.int8)

    # Second-level targets
    t1 = (carrier ^ fused_bg1).astype(np.int8)
    t2 = (carrier ^ fused_bg2).astype(np.int8)

    q3, q4 = _fuse_with_targets_under_secret_constraint(t1, t2, secret)

    assert np.array_equal(q3 | q4, secret), "Scheme II: OR constraint violated!"

    _save_scheme("Scheme2_OneMeaningful", secret, q3, q4)

    _, _, token = stack_and_decode(q3, q4)
    status = "SUCCESS" if token == TEST_TOKEN else f"FAILED (got {token})"
    print(f"  Decode: {status}")


# ---------------------------------------------------------------------------
# Scheme III: Two-Meaningful (ROI, saliency, budget)
# ---------------------------------------------------------------------------

def scheme_3_two_meaningful() -> None:
    """Scheme III: ROI injection with saliency-guided budgeted fusion."""
    np.random.seed(42)
    print("=== Scheme III: Two-Meaningful ===")

    secret = _generate_qr_modules(TEST_TOKEN)
    carrier_a = _generate_qr_modules(CARRIER_A)
    carrier_b = _generate_qr_modules(CARRIER_B)

    s1, s2 = _generate_non_expansion_shadows(secret)

    # Color background -> binary
    color_bg = _color_background(secret.shape, seed=7)
    gray = (0.299 * color_bg[:, :, 0] + 0.587 * color_bg[:, :, 1] + 0.114 * color_bg[:, :, 2]).astype(np.float64)
    bg_bin = (gray > 128).astype(np.int8)

    # ROI: center 15x15 region (avoids finder patterns)
    h, w = secret.shape
    roi_r0, roi_r1 = 7, h - 7
    roi_c0, roi_c1 = 7, w - 7

    bg1 = bg_bin.copy()
    bg2 = bg_bin.copy()
    bg1[roi_r0:roi_r1, roi_c0:roi_c1] = s1[roi_r0:roi_r1, roi_c0:roi_c1]
    bg2[roi_r0:roi_r1, roi_c0:roi_c1] = s2[roi_r0:roi_r1, roi_c0:roi_c1]

    # Saliency & masks
    saliency = _grayscale_saliency(color_bg)
    func_mask = _functional_mask_like_qr(secret.shape)

    # Targets for fusion (ideal carrier-like outputs)
    t1 = (carrier_a ^ bg1).astype(np.int8)
    t2 = (carrier_b ^ bg2).astype(np.int8)

    # --- Budgeted fusion: guarantee q3 OR q4 == secret everywhere ---
    #
    # Step 1: Full constraint fusion for secret-satisfying result.
    q3, q4 = _fuse_with_targets_under_secret_constraint(t1, t2, secret)
    assert np.array_equal(q3 | q4, secret), "Scheme III: initial fusion violated constraint"

    # Step 2: Saliency-guided budget controls how many non-functional ROI
    # positions are allowed to deviate from the carriers.  We identify the
    # budget positions with lowest saliency and keep them (these are the
    # "invisible" spots where deviations are least noticeable).  The budget
    # is informational — the full fusion already guarantees decode.
    budget = int(0.30 * secret.size)

    # Candidate positions: in ROI, not in functional area
    roi_mask = np.zeros(secret.shape, dtype=bool)
    roi_mask[roi_r0:roi_r1, roi_c0:roi_c1] = True
    candidate_mask = roi_mask & ~func_mask

    cand_rows, cand_cols = np.where(candidate_mask)
    if len(cand_rows) == 0:
        print("  WARNING: no candidate positions, skipping")
        return

    # Sort candidates by saliency ascending (least salient = safest to modify)
    sal_vals = saliency[cand_rows, cand_cols]
    order = np.argsort(sal_vals)
    n_use = min(budget, len(order))

    # Count deviations from targets among budgeted positions (informational)
    use_idx = order[:n_use]
    mod_rows = cand_rows[use_idx]
    mod_cols = cand_cols[use_idx]
    deviates = ((q3[mod_rows, mod_cols] != t1[mod_rows, mod_cols]) |
                (q4[mod_rows, mod_cols] != t2[mod_rows, mod_cols])).sum()

    _save_scheme("Scheme3_TwoMeaningful", secret, q3, q4)

    _, _, token = stack_and_decode(q3, q4)
    status = "SUCCESS" if token == TEST_TOKEN else f"FAILED (got {token})"
    print(f"  Decode: {status}")
    print(f"  Budgeted positions: {n_use} / {secret.size} ({100 * n_use / secret.size:.1f}%)")
    print(f"  Deviations from carriers at budgeted positions: {deviates}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    scheme_1_bvc()
    scheme_2_one_meaningful()
    scheme_3_two_meaningful()
    print("\nAll schemes completed.")


if __name__ == "__main__":
    main()
