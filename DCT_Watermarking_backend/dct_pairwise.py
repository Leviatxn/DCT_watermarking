import cv2
import numpy as np

# --- 1. ค่าคงที่ใหม่สำหรับสถาปัตยกรรม Pairwise ---
BLOCK_SIZE = 8
# T คือ "Threshold" (ความแรง) ที่เราจะบังคับให้ค่าคู่ต่างกัน
T = 10 
KEY = 42 # กุญแจสำหรับสุ่มลำดับบล็อกและเลือกคู่

MID_BAND = [(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2),(1,4),(4,1)]
N_MID_BAND = len(MID_BAND)

def pad_to_multiple(img, block_size=8):
    """Pad ภาพเพื่อให้หาร block_size ลงตัว"""
    h, w = img.shape
    ph = (block_size - (h % block_size)) % block_size
    pw = (block_size - (w % block_size)) % block_size
    if ph > 0 or pw > 0:
        # ใช้ 'reflect' เพื่อให้ขอบเนียนขึ้น
        img = np.pad(img, ((0, ph), (0, pw)), mode='reflect')
    return img, (h, w) # คืนขนาดเดิมไว้ใช้ตอน unpad

def unpad_image(img, original_shape):
    """ตัดส่วนที่ pad ออก"""
    h, w = original_shape
    return img[:h, :w]

# --- 2. (ใหม่) ฟังก์ชันสำหรับ ECC (Repetition) ---
def encode_repetition(bits, repeat=3):
    """ขยายบิตโดยการทำซ้ำ เช่น [1,0] -> [1,1,1, 0,0,0]"""
    return np.repeat(bits, repeat)

def decode_repetition(bits_rep, repeat=3):
    """กู้คืนบิตโดยใช้เสียงข้างมาก (Majority Vote)"""
    # ตรวจสอบว่าความยาวหารลงตัว
    if len(bits_rep) % repeat != 0:
        pad_len = repeat - (len(bits_rep) % repeat)
        bits_rep = np.pad(bits_rep, (0, pad_len), 'constant', constant_values=0)
        
    bits_rep = bits_rep.reshape(-1, repeat)
    sums = bits_rep.sum(axis=1)
    # ถ้าผลรวมมากกว่าครึ่ง (เช่น >= 2 ใน 3) ถือเป็น 1
    return (sums >= (repeat // 2 + 1)).astype(np.uint8)

# --- 3. (ผ่าตัดใหม่) ฟังก์ชัน Embed ---
def embed_dct_pairwise(img, watermark_bits_encoded, key=KEY, T=T):
    """
    ฝังบิตลายน้ำ (ที่เข้ารหัส ECC แล้ว) โดยใช้ Pairwise Difference
    img: ภาพต้นฉบับ (0-255, uint8)
    watermark_bits_encoded: บิตลายน้ำที่ขยายด้วย ECC แล้ว (เช่น [1,1,1, 0,0,0, ...])
    """
    
    h, w = img.shape
    # ตรวจสอบว่าภาพมีขนาดหาร 8 ลงตัว (ควร pad ภาพก่อนเรียกใช้)
    if h % BLOCK_SIZE != 0 or w % BLOCK_SIZE != 0:
        raise ValueError("ขนาดภาพต้องหาร 8 ลงตัว (ควร Pad ภาพก่อน)")

    watermarked = np.zeros_like(img, dtype=np.float32)
    
    nb_h = h // BLOCK_SIZE
    nb_w = w // BLOCK_SIZE
    total_blocks = nb_h * nb_w
    
    # --- ตรรกะการสุ่มลำดับบล็อก (สำคัญมาก) ---
    rng_master = np.random.RandomState(key)
    block_ids = np.arange(total_blocks)
    rng_master.shuffle(block_ids) # สลับลำดับบล็อกที่จะใช้
    
    bit_idx = 0
    
    # วนลูปตามลำดับบล็อกที่สุ่มแล้ว
    for b_id in block_ids:
        if bit_idx >= len(watermark_bits_encoded):
            break # ฝังครบทุกบิตแล้ว
            
        by = b_id // nb_w
        bx = b_id % nb_w
        
        # ดึงบล็อกต้นฉบับ
        block = img[by*BLOCK_SIZE:(by+1)*BLOCK_SIZE, bx*BLOCK_SIZE:(bx+1)*BLOCK_SIZE]
        dct_block = cv2.dct(np.float32(block))
        
        # --- นี่คือหัวใจของ Pairwise ---
        
        # 1. เลือก "คู่" ที่จะใช้ โดยใช้ key + b_id เพื่อให้ deterministic
        rng_block = np.random.RandomState(key + b_id)
        idx1 = rng_block.randint(N_MID_BAND)
        idx2 = (idx1 + 1 + rng_block.randint(N_MID_BAND - 1)) % N_MID_BAND
        (u1, v1) = MID_BAND[idx1]
        (u2, v2) = MID_BAND[idx2]
        
        c1 = dct_block[u1, v1]
        c2 = dct_block[u2, v2]
        diff = c1 - c2
        
        bit = watermark_bits_encoded[bit_idx]
        
        # 2. บังคับความสัมพันธ์
        if bit == 1:
            if diff < T: # ถ้า c1 - c2 ยังไม่มากพอ
                shift = (T - diff) / 2.0
                dct_block[u1, v1] += shift
                dct_block[u2, v2] -= shift
        else: # bit == 0
            if diff > -T: # ถ้า c1 - c2 ยังไม่ "ติดลบ" มากพอ
                shift = (T + diff) / 2.0
                dct_block[u1, v1] -= shift
                dct_block[u2, v2] += shift
        # ---------------------------------

        watermarked[by*BLOCK_SIZE:(by+1)*BLOCK_SIZE, bx*BLOCK_SIZE:(bx+1)*BLOCK_SIZE] = cv2.idct(dct_block)
        bit_idx += 1

    # คัดลอกบล็อกที่ไม่ได้ใช้ (บล็อกที่เหลือ) จากภาพต้นฉบับ
    unused_blocks = block_ids[bit_idx:]
    for b_id in unused_blocks:
        by = b_id // nb_w
        bx = b_id % nb_w
        block = img[by*BLOCK_SIZE:(by+1)*BLOCK_SIZE, bx*BLOCK_SIZE:(bx+1)*BLOCK_SIZE]
        watermarked[by*BLOCK_SIZE:(by+1)*BLOCK_SIZE, bx*BLOCK_SIZE:(bx+1)*BLOCK_SIZE] = block

    return np.clip(watermarked, 0, 255).astype(np.uint8)


# --- 4. (ผ่าตัดใหม่) ฟังก์ชัน Extract ---
def extract_dct_pairwise(watermarked, num_bits_encoded, key=KEY):
    """
    สกัดบิตลายน้ำ (ที่ยังเข้ารหัส ECC) ออกมา
    watermarked: ภาพที่มีลายน้ำ (0-255, uint8)
    num_bits_encoded: "จำนวน" บิตที่ถูกฝังไป (รวม ECC แล้ว)
    """
    h, w = watermarked.shape
    if h % BLOCK_SIZE != 0 or w % BLOCK_SIZE != 0:
        raise ValueError("ขนาดภาพต้องหาร 8 ลงตัว")

    nb_h = h // BLOCK_SIZE
    nb_w = w // BLOCK_SIZE
    total_blocks = nb_h * nb_w

    # --- ตรรกะการสุ่มลำดับบล็อก (ต้องเหมือนตอนฝังเป๊ะๆ) ---
    rng_master = np.random.RandomState(key)
    block_ids = np.arange(total_blocks)
    rng_master.shuffle(block_ids)

    extracted_bits = []
    
    # วนลูปตามลำดับบล็อกที่สุ่มแล้ว
    for b_id in block_ids:
        if len(extracted_bits) >= num_bits_encoded:
            break # สกัดครบแล้ว
            
        by = b_id // nb_w
        bx = b_id % nb_w
        
        block = watermarked[by*BLOCK_SIZE:(by+1)*BLOCK_SIZE, bx*BLOCK_SIZE:(bx+1)*BLOCK_SIZE]
        dct_block = cv2.dct(np.float32(block))

        # --- นี่คือหัวใจของการสกัด Pairwise ---
        
        # 1. เลือก "คู่" เดิมเป๊ะๆ
        rng_block = np.random.RandomState(key + b_id)
        idx1 = rng_block.randint(N_MID_BAND)
        idx2 = (idx1 + 1 + rng_block.randint(N_MID_BAND - 1)) % N_MID_BAND
        (u1, v1) = MID_BAND[idx1]
        (u2, v2) = MID_BAND[idx2]
        
        c1 = dct_block[u1, v1]
        c2 = dct_block[u2, v2]
        
        # 2. ตรวจสอบความสัมพันธ์
        if (c1 - c2) > 0:
            extracted_bits.append(1)
        else:
            extracted_bits.append(0)
        # ---------------------------------
        
    # ถ้าสกัดบิตได้ไม่ครบ (เช่น ภาพถูกตัด) ให้เติม 0
    if len(extracted_bits) < num_bits_encoded:
        extracted_bits.extend([0] * (num_bits_encoded - len(extracted_bits)))

    return np.array(extracted_bits, dtype=np.uint8)

# --- 5. (ใหม่) ตัวอย่างการใช้งาน ---
if __name__ == '__main__':
    
    # --- 1. เตรียมข้อมูล ---
    try:
        # ลองโหลดภาพ camera มาตรฐาน (512x512)
        from skimage import data
        img = data.camera() # เป็น uint8, 0-255 อยู่แล้ว
    except ImportError:
        # ถ้าไม่มี skimage, สร้างภาพ Noise จำลอง
        print("skimage not found, creating dummy image.")
        img = np.random.randint(0, 256, (512, 512), dtype=np.uint8)

    # สร้างลายน้ำต้นฉบับ (เช่น 100 บิต)
    np.random.seed(KEY)
    original_watermark_bits = np.random.randint(0, 2, 100, dtype=np.uint8)
    
    REPETITION = 3 # ฝังซ้ำ 3 ครั้ง

    # --- 2. เข้ารหัส ECC ---
    bits_to_embed = encode_repetition(original_watermark_bits, REPETITION)
    print(f"Original bits: {len(original_watermark_bits)}")
    print(f"ECC Encoded bits to embed: {len(bits_to_embed)}")

    # --- 3. ฝังลายน้ำ ---
    # (หมายเหตุ: ภาพ 512x512 มี (512/8)*(512/8) = 4096 บล็อก, ฝัง 300 บิตได้สบาย)
    print("Embedding watermark...")
    watermarked_image = embed_dct_pairwise(img, bits_to_embed, key=KEY, T=T)
    
    # --- 4. สกัดลายน้ำ (แบบไม่โจมตี) ---
    print("Extracting (no attack)...")
    extracted_encoded_bits = extract_dct_pairwise(watermarked_image, len(bits_to_embed), key=KEY)
    
    # --- 5. ถอดรหัส ECC ---
    extracted_bits = decode_repetition(extracted_encoded_bits, REPETITION)
    
    # --- 6. ตรวจสอบผลลัพธ์ ---
    # ตัดให้เหลือขนาดเท่า original (เผื่อ decode ได้บิตเกินมา)
    extracted_bits = extracted_bits[:len(original_watermark_bits)] 
    
    bit_errors = np.sum(original_watermark_bits != extracted_bits)
    ber = (bit_errors / len(original_watermark_bits)) * 100
    
    print(f"\n--- Results (No Attack) ---")
    print(f"Original bits:  {original_watermark_bits[:20]}...")
    print(f"Extracted bits: {extracted_bits[:20]}...")
    print(f"Total Bit Errors: {bit_errors} / {len(original_watermark_bits)}")
    print(f"Bit Error Rate (BER): {ber:.2f}%")