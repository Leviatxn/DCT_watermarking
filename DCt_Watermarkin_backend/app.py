from flask import Flask, request, send_file
from flask_cors import CORS
import cv2
import numpy as np
import os

# --- 1. เปลี่ยนการ import ---
# (สมมติว่าคุณตั้งชื่อไฟล์ใหม่ว่า dct_pairwise.py)
from dct_pairwise import (
    embed_dct_pairwise, 
    extract_dct_pairwise,
    encode_repetition,
    decode_repetition,
    pad_to_multiple,
    unpad_image
)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# --- 2. เพิ่มค่าคงที่สำหรับอัลกอริทึมใหม่ ---
KEY = 42      # กุญแจลับ ต้องเหมือนกันทั้งตอนฝังและสกัด
T = 10        # ความแรงของการฝัง (Threshold)
REPETITION = 3  # จำนวนการฝังซ้ำ (ECC)
WM_SHAPE = (32, 32) # ขนาดมาตรฐานของลายน้ำ

@app.route("/embed", methods=["POST"])
def embed():
    img_file = request.files["image"]
    wm_file = request.files["watermark"]

    img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
    wm_path = os.path.join(UPLOAD_FOLDER, wm_file.filename)
    img_file.save(img_path)
    wm_file.save(wm_path)

    # --- 3. ปรับปรุงตรรกะการฝัง ---
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    wm_img = cv2.imread(wm_path, cv2.IMREAD_GRAYSCALE)

    # ก. Pad ภาพหลักให้หาร 8 ลงตัว
    img_padded, original_shape = pad_to_multiple(img, block_size=8)
    
    # ข. เตรียมลายน้ำ (เหมือนเดิม แต่เปลี่ยนเป็น WM_SHAPE)
    wm_resized = cv2.resize(wm_img, WM_SHAPE)
    _, wm_binary = cv2.threshold(wm_resized, 127, 1, cv2.THRESH_BINARY)
    
    # ค. แปลงลายน้ำ 2D -> 1D bit array
    original_watermark_bits = wm_binary.flatten() # (ได้ 32*32 = 1024 บิต)
    
    # ง. เข้ารหัส ECC (ขยายบิต 3 เท่า)
    bits_to_embed = encode_repetition(original_watermark_bits, REPETITION) # (ได้ 1024*3 = 3072 บิต)

    # จ. เรียกฟังก์ชันฝังลายน้ำตัวใหม่
    watermarked_img_padded = embed_dct_pairwise(
        img_padded, 
        bits_to_embed, 
        key=KEY, 
        T=T
    )
    
    # ฉ. (สำคัญ) ตัดส่วนที่ pad ทิ้ง
    watermarked_img = unpad_image(watermarked_img_padded, original_shape)

    out_path = os.path.join(RESULT_FOLDER, "watermarked.png")
    cv2.imwrite(out_path, watermarked_img)

    return send_file(out_path, mimetype="image/png")

@app.route("/extract", methods=["POST"])
def extract():
    img_file = request.files["image"]
    img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
    img_file.save(img_path)

    # --- 4. ปรับปรุงตรรกะการสกัด ---
    watermarked = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

    # ก. Pad ภาพที่รับมา (ต้องทำเหมือนตอนฝังเป๊ะๆ)
    watermarked_padded, original_shape = pad_to_multiple(watermarked, block_size=8)

    # ข. คำนวณจำนวนบิตที่ต้องสกัด
    num_original_bits = WM_SHAPE[0] * WM_SHAPE[1]           # 1024
    num_encoded_bits = num_original_bits * REPETITION     # 3072
    
    # ค. เรียกฟังก์ชันสกัดตัวใหม่
    extracted_encoded_bits = extract_dct_pairwise(
        watermarked_padded, 
        num_encoded_bits, 
        key=KEY
    )
    
    # ง. ถอดรหัส ECC (ซ่อมบิตที่ผิดพลาด)
    extracted_bits = decode_repetition(extracted_encoded_bits, REPETITION)
    
    # จ. ตัดให้เหลือขนาดบิตดั้งเดิม
    extracted_bits = extracted_bits[:num_original_bits]
    
    # ฉ. แปลง 1D bit array -> 2D image array
    extracted_img_array = extracted_bits.reshape(WM_SHAPE)
    
    # ช. แปลงเป็นภาพที่มองเห็นได้ (0/1 -> 0/255)
    extracted_img = (extracted_img_array * 255).astype(np.uint8)

    out_path = os.path.join(RESULT_FOLDER, "extracted.png")
    cv2.imwrite(out_path, extracted_img)
    return send_file(out_path, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)