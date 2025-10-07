import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.metrics import peak_signal_noise_ratio as psnr, structural_similarity as ssim

BLOCK_SIZE = 8
ALPHA = 10  
MID_BAND = [
    (0,2),(0,3),(1,1),(1,2),(1,3),
    (2,0),(2,1),(2,2),(3,0),(3,1)
]  # mid-frequency positions


def embed_dct_midband(img, watermark):
    h, w = img.shape
    wm_h, wm_w = watermark.shape
    watermarked = np.zeros_like(img, dtype=np.float32)
    idx = 0

    for i in range(0, h, BLOCK_SIZE):
        for j in range(0, w, BLOCK_SIZE):
            block = img[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE]
            if block.shape[0] != BLOCK_SIZE or block.shape[1] != BLOCK_SIZE:
                continue

            dct_block = cv2.dct(np.float32(block))
            bit = watermark.flat[idx % (wm_h * wm_w)]
            (u, v) = MID_BAND[idx % len(MID_BAND)]

            # ฝังบิต: ปรับค่าความถี่กลาง
            dct_block[u, v] += ALPHA if bit == 1 else -ALPHA

            watermarked[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE] = cv2.idct(dct_block)
            idx += 1

    return np.clip(watermarked, 0, 255).astype(np.uint8)


##DCT Watermark Extraction

def extract_dct_midband(watermarked, wm_shape):
    h, w = watermarked.shape
    bits = []
    idx = 0

    for i in range(0, h, BLOCK_SIZE):
        for j in range(0, w, BLOCK_SIZE):
            block = watermarked[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE]
            if block.shape[0] != BLOCK_SIZE or block.shape[1] != BLOCK_SIZE:
                continue

            dct_block = cv2.dct(np.float32(block))
            (u, v) = MID_BAND[idx % len(MID_BAND)]

            bit = 1 if dct_block[u, v] > 0 else 0
            bits.append(bit)
            idx += 1
            if idx >= wm_shape[0] * wm_shape[1]:
                break
        if idx >= wm_shape[0] * wm_shape[1]:
            break

    wm = np.array(bits).reshape(wm_shape)
    return wm


##Test the algorithm

img = cv2.imread("test.jpg", cv2.IMREAD_GRAYSCALE)

# สร้างลายน้ำ (หรือจะโหลดจากไฟล์ก็ได้)
np.random.seed(42)
watermark = np.random.randint(0, 2, (32, 32))

# ฝังลายน้ำ
wm_img = embed_dct_midband(img, watermark)

# ดึงกลับ
extracted = extract_dct_midband(wm_img, watermark.shape)


psnr_val = psnr(img, wm_img)
ssim_val = ssim(img, wm_img)

print(f"PSNR = {psnr_val:.2f} dB, SSIM = {ssim_val:.3f}")


plt.figure(figsize=(12,6))
plt.subplot(1,3,1); plt.title("Original Image"); plt.imshow(img, cmap='gray'); plt.axis('off')
plt.subplot(1,3,2); plt.title("Watermarked Image"); plt.imshow(wm_img, cmap='gray'); plt.axis('off')
plt.subplot(1,3,3); plt.title("Extracted Watermark"); plt.imshow(extracted, cmap='gray'); plt.axis('off')
plt.show()
