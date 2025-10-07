#!/usr/bin/env python3
"""
DCT pairwise watermark embed/extract (blind) with simple ECC (3x repetition)
Includes tests: JPEG compression, Gaussian noise, resize
Author: ChatGPT (template for project)
"""

import os
import math
import cv2
import numpy as np
from skimage import data, color
from skimage.metrics import peak_signal_noise_ratio as psnr, structural_similarity as ssim
from PIL import Image
import io

# ---------------------------
# Utilities
# ---------------------------
def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def load_image_grayscale(path=None, target_size=None):
    if path is not None and os.path.isfile(path):
        im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if im is None:
            raise ValueError(f"Failed to read image at {path}")
        im = im.astype(np.float32) / 255.0
    else:
        im = data.camera().astype(np.float32) / 255.0
    if target_size is not None:
        w,h = target_size
        im = cv2.resize(im, (w,h), interpolation=cv2.INTER_AREA)
    return im

def pad_to_multiple(img, block=8):
    h,w = img.shape
    ph = (block - (h % block)) % block
    pw = (block - (w % block)) % block
    if ph>0 or pw>0:
        img = np.pad(img, ((0,ph),(0,pw)), mode='reflect')
    return img

def psnr_ssim_pair(gt, img):
    return psnr((gt*255).astype(np.uint8), (np.clip(img,0,1)*255).astype(np.uint8), data_range=255), \
           ssim((gt*255).astype(np.uint8), (np.clip(img,0,1)*255).astype(np.uint8), data_range=255)

# ---------------------------
# DCT helpers
# ---------------------------
def block_view(a, block=(8,8)):
    """Return view of image as blocks; shape (n_bh, n_bw, bh, bw)"""
    h,w = a.shape
    bh,bw = block
    assert h % bh == 0 and w % bw == 0
    return a.reshape(h//bh, bh, w//bw, bw).swapaxes(1,2)

def block_iter(a, block=(8,8)):
    """Yield (i,j, block_array) for non-overlapping blocks"""
    h,w = a.shape
    bh,bw = block
    nb_h = h // bh
    nb_w = w // bw
    for by in range(nb_h):
        for bx in range(nb_w):
            yield by, bx, a[by*bh:(by+1)*bh, bx*bw:(bx+1)*bw]

def dct2(block):
    """2D DCT type II using cv2 (expects float32)"""
    return cv2.dct(block)

def idct2(coeff):
    """2D inverse DCT using cv2"""
    return cv2.idct(coeff)

# ---------------------------
# Simple ECC: 3x repetition
# ---------------------------
def encode_repetition(bits, repeat=3):
    return np.repeat(bits, repeat)

def decode_repetition(bits_rep, repeat=3):
    # bits_rep is 0/1 array length multiple of repeat
    bits_rep = bits_rep.reshape(-1, repeat)
    sums = bits_rep.sum(axis=1)
    return (sums >= (repeat//2 + 1)).astype(np.uint8)  # majority

# ---------------------------
# Message conversion
# ---------------------------
def text_to_bits(s):
    b = []
    for ch in s:
        bits = bin(ord(ch))[2:].rjust(8, '0')
        b.extend([int(x) for x in bits])
    return np.array(b, dtype=np.uint8)

def bits_to_text(bits):
    # bits length must be multiple of 8
    s = ""
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        c = int("".join(str(int(x)) for x in byte.tolist()), 2)
        s += chr(c)
    return s

# ---------------------------
# Embedding / Extraction (Pairwise)
# ---------------------------
# mid-band candidate positions for 8x8 DCT (u,v)
MID_BAND = [(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2),(1,4),(4,1)]

def generate_block_order(h_blocks, w_blocks, key):
    rng = np.random.RandomState(key)
    idxs = np.arange(h_blocks * w_blocks)
    rng.shuffle(idxs)
    return idxs.reshape(h_blocks, w_blocks)

def select_positions_for_block(by, bx, total_choices, rng):
    # here we pick deterministic or random choice - use rng.choice
    # returns two distinct indices into MID_BAND
    idx = rng.randint(len(MID_BAND))
    idx2 = (idx + 1 + rng.randint(len(MID_BAND)-1)) % len(MID_BAND)
    return MID_BAND[idx], MID_BAND[idx2]

def embed_pairwise_dct(y, message_bits, key=1234, T=8, usage_ratio=0.4):
    """
    y: float image [0,1], single channel (Y)
    message_bits: array of 0/1 bits (already ECC-encoded)
    key: int seed
    T: threshold to enforce difference
    usage_ratio: fraction of total blocks used for embedding
    """
    h,w = y.shape
    bh = bw = 8
    assert h % bh == 0 and w % bw == 0
    nb_h = h // bh
    nb_w = w // bw
    total_blocks = nb_h * nb_w
    n_to_use = int(total_blocks * usage_ratio)
    if n_to_use <= 0:
        raise ValueError("usage_ratio too small for image size")
    # prepare rng
    rng = np.random.RandomState(key)
    # flatten blocks order
    block_ids = np.arange(total_blocks)
    rng.shuffle(block_ids)
    used_blocks = block_ids[:n_to_use]

    # copy y to work on
    y_w = y.copy()
    bit_idx = 0
    applied = 0

    for b_id in used_blocks:
        if bit_idx >= len(message_bits):
            break
        by = b_id // nb_w
        bx = b_id % nb_w
        block = y_w[by*bh:(by+1)*bh, bx*bw:(bx+1)*bw].astype(np.float32)
        C = dct2(block)
        # choose pair positions using rng seeded by key + block id (so deterministic)
        r2 = np.random.RandomState(key + b_id)
        (u1,v1), (u2,v2) = select_positions_for_block(by, bx, len(MID_BAND), r2)
        c1 = C[u1, v1]
        c2 = C[u2, v2]
        bit = int(message_bits[bit_idx])
        diff = c1 - c2
        # enforce threshold T for bit
        if bit == 1:
            if diff < T:
                shift = (T - diff) / 2.0 + 1e-6
                C[u1,v1] = c1 + shift
                C[u2,v2] = c2 - shift
        else:
            if -diff < T:
                shift = (T + diff) / 2.0 + 1e-6
                C[u1,v1] = c1 - shift
                C[u2,v2] = c2 + shift
        # inverse
        block_rec = idct2(C)
        y_w[by*bh:(by+1)*bh, bx*bw:(bx+1)*bw] = block_rec
        bit_idx += 1
        applied += 1

    if bit_idx < len(message_bits):
        print(f"[WARN] Not enough blocks to embed all bits ({bit_idx}/{len(message_bits)})")
    return np.clip(y_w, 0, 1), applied

def extract_pairwise_dct(y_sus, msg_len_bits, key=1234, T=8, usage_ratio=0.4):
    """
    Extract msg_len_bits bits (before ECC) from suspect image y_sus
    Returns extracted bits array (length = msg_len_bits)
    """
    h,w = y_sus.shape
    bh = bw = 8
    assert h % bh == 0 and w % bw == 0
    nb_h = h // bh
    nb_w = w // bw
    total_blocks = nb_h * nb_w
    n_to_use = int(total_blocks * usage_ratio)

    rng = np.random.RandomState(key)
    block_ids = np.arange(total_blocks)
    rng.shuffle(block_ids)
    used_blocks = block_ids[:n_to_use]

    extracted = []
    bit_idx = 0
    for b_id in used_blocks:
        if bit_idx >= msg_len_bits:
            break
        by = b_id // nb_w
        bx = b_id % nb_w
        block = y_sus[by*bh:(by+1)*bh, bx*bw:(bx+1)*bw].astype(np.float32)
        C = dct2(block)
        r2 = np.random.RandomState(key + b_id)
        (u1,v1), (u2,v2) = select_positions_for_block(by, bx, len(MID_BAND), r2)
        c1 = C[u1, v1]
        c2 = C[u2, v2]
        extracted_bit = 1 if (c1 - c2) > 0 else 0
        extracted.append(extracted_bit)
        bit_idx += 1

    # if not enough bits extracted, pad zeros
    if len(extracted) < msg_len_bits:
        extracted.extend([0] * (msg_len_bits - len(extracted)))
    return np.array(extracted, dtype=np.uint8)

# ---------------------------
# Attacks / Transformations
# ---------------------------
def apply_jpeg_bytes(img_float, quality=90):
    """Compress-decompress using JPEG in memory using PIL (img_float in [0,1])"""
    img_uint8 = (np.clip(img_float,0,1) * 255).astype(np.uint8)
    pil = Image.fromarray(img_uint8)
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=int(quality))
    buf.seek(0)
    pil2 = Image.open(buf)
    arr = np.array(pil2).astype(np.float32) / 255.0
    if arr.ndim == 3:
        arr = color.rgb2gray(arr)  # fallback, but our images are grayscale
    return arr

def apply_gaussian_noise(img_float, sigma=0.01):
    noisy = img_float + np.random.normal(0, sigma, img_float.shape)
    return np.clip(noisy, 0, 1)

def apply_resize(img_float, scale=0.5):
    h,w = img_float.shape
    small = cv2.resize((img_float*255).astype(np.uint8), (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
    up = cv2.resize(small, (w,h), interpolation=cv2.INTER_CUBIC)
    return up.astype(np.float32)/255.0

# ---------------------------
# Demo / Main
# ---------------------------
def load_image_grayscale(path=None, target_size=None):
    """
    Load grayscale float image in range [0,1].
    If path is None or not found, fallback to skimage's camera.
    If target_size=None → ใช้ขนาดเดิมของภาพ input
    """
    if path is not None and os.path.isfile(path):
        im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if im is None:
            raise ValueError(f"Failed to read image at {path}")
        im = im.astype(np.float32) / 255.0
    else:
        im = data.camera().astype(np.float32) / 255.0

    if target_size is not None:
        w, h = target_size
        im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    return im


def main():
    outd = "results_dct_pairwise"
    ensure_dir(outd)

    # parameters
    input_path = "test.jpg"  # หรือปล่อยว่างจะใช้ camera()
    target_size = None  # ✅ ใช้ขนาดจริงของภาพ input โดย default
    key = 2025
    T = 8
    usage = 0.5  # ใช้ 50% ของ blocks
    repeat = 3   # ECC repetition
    

    # load
    print("Loading image...")
    y = load_image_grayscale(input_path, target_size=target_size)
    y = pad_to_multiple(y, 8)
    print("Image shape:", y.shape)

    # message to embed
    message = "Author:Alice;ID:0001"  # can change
    bits = text_to_bits(message)
    print("Original message bits:", len(bits))
    bits_enc = encode_repetition(bits, repeat=repeat)
    print("After repetition ECC bits:", len(bits_enc))

    # embed
    print("Embedding message ...")
    y_watermarked, applied = embed_pairwise_dct(y, bits_enc, key=key, T=T, usage_ratio=usage)
    print(f"Applied bits: {applied}")

    # Save watermarked image
    wm_uint8 = (np.clip(y_watermarked,0,1)*255).astype(np.uint8)
    cv2.imwrite(os.path.join(outd, "watermarked.png"), wm_uint8)
    print("Saved watermarked.png")

    # extraction (no attack)
    print("Extracting from watermarked (no attack)...")
    # we expect to extract len(bits_enc) bits, then decode by repetition and compare to original bits
    extracted_bits_enc = extract_pairwise_dct(y_watermarked, msg_len_bits=len(bits_enc), key=key, T=T, usage_ratio=usage)
    # decode repetition
    extracted_bits = decode_repetition(extracted_bits_enc, repeat=repeat)
    recovered_text = bits_to_text(extracted_bits[:len(bits)])
    bit_errors = np.mean(extracted_bits[:len(bits)] != bits)
    print("Recovered text (no attack):", recovered_text)
    print(f"BER (no attack) = {bit_errors:.4f}")

    # Evaluate imperceptibility
    p,s = psnr_ssim_pair(y, y_watermarked)
    print(f"Imperceptibility: PSNR={p:.2f} dB, SSIM={s:.4f}")

    # --------------------
    # Robustness tests
    # --------------------
    tests = []
    # JPEG qualities
    for Q in [95,85,75,65,50]:
        attacked = apply_jpeg_bytes(y_watermarked, quality=Q)
        extracted_enc = extract_pairwise_dct(attacked, msg_len_bits=len(bits_enc), key=key, T=T, usage_ratio=usage)
        decoded = decode_repetition(extracted_enc, repeat=repeat)
        ber = np.mean(decoded[:len(bits)] != bits)
        rec_text = bits_to_text(decoded[:len(bits)])
        p_att, s_att = psnr_ssim_pair(y, attacked)
        tests.append(('JPEG', Q, ber, rec_text, p_att, s_att))
        # save attacked image
        cv2.imwrite(os.path.join(outd, f"attacked_jpeg_Q{Q}.png"), (attacked*255).astype(np.uint8))

    # Gaussian noise
    for sigma in [0.005, 0.01, 0.02]:
        attacked = apply_gaussian_noise(y_watermarked, sigma=sigma)
        extracted_enc = extract_pairwise_dct(attacked, msg_len_bits=len(bits_enc), key=key, T=T, usage_ratio=usage)
        decoded = decode_repetition(extracted_enc, repeat=repeat)
        ber = np.mean(decoded[:len(bits)] != bits)
        rec_text = bits_to_text(decoded[:len(bits)])
        p_att, s_att = psnr_ssim_pair(y, attacked)
        tests.append(('Noise', sigma, ber, rec_text, p_att, s_att))
        cv2.imwrite(os.path.join(outd, f"attacked_noise_{sigma:.3f}.png"), (attacked*255).astype(np.uint8))

    # Resize
    for scale in [0.9, 0.7, 0.5]:
        attacked = apply_resize(y_watermarked, scale=scale)
        extracted_enc = extract_pairwise_dct(attacked, msg_len_bits=len(bits_enc), key=key, T=T, usage_ratio=usage)
        decoded = decode_repetition(extracted_enc, repeat=repeat)
        ber = np.mean(decoded[:len(bits)] != bits)
        rec_text = bits_to_text(decoded[:len(bits)])
        p_att, s_att = psnr_ssim_pair(y, attacked)
        tests.append(('Resize', scale, ber, rec_text, p_att, s_att))
        cv2.imwrite(os.path.join(outd, f"attacked_resize_{int(scale*100)}.png"), (attacked*255).astype(np.uint8))

    # Print summary
    print("\n=== Robustness Summary ===")
    print("Type\tParam\tBER\tRecovered text (prefix)\tPSNR\tSSIM")
    for t in tests:
        print(f"{t[0]}\t{t[1]}\t{t[2]:.4f}\t{t[3][:40]}\t{t[4]:.2f}\t{t[5]:.4f}")

    # Save watermarked comparison
    cv2.imwrite(os.path.join(outd, "orig.png"), (y*255).astype(np.uint8))
    cv2.imwrite(os.path.join(outd, "watermarked_small.png"), (wm_uint8).astype(np.uint8))
    print("All results saved to", outd)

if __name__ == "__main__":
    main()
