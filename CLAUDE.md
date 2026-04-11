# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A QR authentication system based on Visual Cryptography (VC). The system splits a secret QR code into two shares — individually meaningless, but recoverable by stacking (OR operation) to produce a scannable QR.

Two implementation layers:
- `main.py` — basic non-expansion (2,2)-VCS flow
- `advanced_schemes.py` — three paper-style schemes (Scheme I: BVC, Scheme II: One-Meaningful, Scheme III: Two-Meaningful) adding carrier QR fusion, backgrounds, ROI, saliency, and error-correction budgets

Supporting files:
- `verify_success.py` — validates that stacked outputs decode correctly
- `requirements.txt` — Python dependencies

## Commands

```bash
pip install -r requirements.txt
python main.py                # Run basic VC flow
python advanced_schemes.py    # Run all three advanced schemes
python verify_success.py      # Verify all output images decode correctly
```

## Core Data Representation

- Module matrices: `1` = black, `0` = white
- Stacking rule: `stack(a, b) = a OR b` (black-dominant)
- Image conversion happens only at I/O boundaries (1→0 pixel, 0→255 pixel)
- Non-expansion (2,2)-VCS: white secret → (0,0); black secret → randomly (1,0) or (0,1)

## Architecture

### main.py — Basic Flow
1. `_generate_qr_modules(data)` → 0/1 module matrix
2. `encrypt_shares(secret)` → share1, share2 via non-expansion VCS
3. `combine_shares(s1, s2)` → stacked = s1 OR s2
4. `decrypt_qr(stacked)` → module matrix (no block downsampling)
5. `authenticate(restored)` → decode with pyzbar, compare token

Output: `Basic_Output/` (original QR, two shares, stacked, restored)

### advanced_schemes.py — Three Schemes
All schemes share: generate secret → produce shadows → fuse with carriers/backgrounds → stack to recover.

Key internal functions:
- `_generate_non_expansion_shadows(secret)` — module-level splitting
- `_fuse_with_targets_under_secret_constraint(...)` — constrained optimization: given target images, find q3/q4 such that `q3 OR q4 = secret` while minimizing visual difference to targets. White→(0,0) only; black→(1,0)/(0,1)/(1,1) pick closest match.
- `_binary_background` / `_color_background` — background generation
- `_grayscale_saliency(...)` — gradient-based saliency estimation
- `_functional_mask_like_qr(...)` — protects finder/timing pattern regions

**Scheme I** (`scheme_1_bvc`): shadows + carrier QR fusion. Targets: `carrier XOR shadow`.

**Scheme II** (`scheme_2_one_meaningful`): two-level fusion. First fuse shadows into binary backgrounds, then fuse results into carrier QR.

**Scheme III** (`scheme_3_two_meaningful`): adds ROI injection, dual carriers, color backgrounds, saliency-guided candidate selection, and error-correction budget (30% of modules). Most covert.

Output per scheme: directory with original QR, two fused shares, stacked, and restored images.

### stack_and_decode (shared)
`stack_and_decode(share1, share2, scale_factor=1)` — OR-stacks two shares, decodes with pyzbar. `scale_factor=1` for non-expansion modules.

## Engineering Approximations vs Paper

The code uses engineering approximations rather than exact paper algorithms:
- RS/PBVM details → module-flip constraint optimization with budget
- ROI/saliency → lightweight gradient saliety + functional-area mask
- This trades theoretical precision for readability and reliable scannable output

## Tunable Parameters (Scheme III)

Impact-ordered: QR version & error-correction level (H), ROI size/position, budget ratio (default 30%), saliency threshold, carrier content complexity.
