from flask import Flask, request, send_file, jsonify # 1. เพิ่ม jsonify
from flask_cors import CORS
import cv2
import numpy as np
import os

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

# ค่าคงที่สำหรับอัลกอริทึม
KEY = 42      
T = 10        
REPETITION = 3  
WM_SHAPE = (32, 32) # ขนาดมาตรฐานของลายน้ำ

@app.route("/embed", methods=["POST"])
def embed():
    img_file = request.files["image"]
    wm_file = request.files["watermark"]

    img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
    wm_path = os.path.join(UPLOAD_FOLDER, wm_file.filename)
    img_file.save(img_path)
    wm_file.save(wm_path)

    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    wm_img = cv2.imread(wm_path, cv2.IMREAD_GRAYSCALE)

    img_padded, original_shape = pad_to_multiple(img, block_size=8)
    
    wm_resized = cv2.resize(wm_img, WM_SHAPE)
    _, wm_binary = cv2.threshold(wm_resized, 127, 1, cv2.THRESH_BINARY)
    
    original_watermark_bits = wm_binary.flatten()
    
    bits_to_embed = encode_repetition(original_watermark_bits, REPETITION) 

    watermarked_img_padded = embed_dct_pairwise(
        img_padded, 
        bits_to_embed, 
        key=KEY, 
        T=T
    )
    
    watermarked_img = unpad_image(watermarked_img_padded, original_shape)

    out_path = os.path.join(RESULT_FOLDER, "watermarked.png")
    cv2.imwrite(out_path, watermarked_img)

    return send_file(out_path, mimetype="image/png")

@app.route("/extract", methods=["POST"])
def extract_and_verify():
    
    img_file = request.files["image"]
    wm_file = request.files["original_watermark"]

    img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
    wm_path = os.path.join(UPLOAD_FOLDER, wm_file.filename)
    img_file.save(img_path)
    wm_file.save(wm_path)

    watermarked = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    watermarked_padded, _ = pad_to_multiple(watermarked, block_size=8)

    #โหลด "ลายน้ำต้นฉบับ" เพื่อใช้เปรียบเทียบ
    wm_img_orig = cv2.imread(wm_path, cv2.IMREAD_GRAYSCALE)
    wm_resized_orig = cv2.resize(wm_img_orig, WM_SHAPE)
    _, wm_binary_orig = cv2.threshold(wm_resized_orig, 127, 1, cv2.THRESH_BINARY)
    
    original_bits = wm_binary_orig.flatten()

    num_original_bits = len(original_bits)                # 1024
    num_encoded_bits = num_original_bits * REPETITION     # 3072
    
    # จ. สกัดลายน้ำ
    extracted_encoded_bits = extract_dct_pairwise(
        watermarked_padded, 
        num_encoded_bits, 
        key=KEY
    )
    
    # ฉ. ถอดรหัส ECC
    extracted_bits = decode_repetition(extracted_encoded_bits, REPETITION)
    extracted_bits = extracted_bits[:num_original_bits] # ตัดให้เหลือขนาดเท่า original
    
    
    # คำนวณ Bit Error Rate (BER)
    if len(original_bits) != len(extracted_bits):
        return jsonify({"error": "Bit length mismatch after decoding."}), 400

    bit_errors = np.sum(original_bits != extracted_bits)
    total_bits = num_original_bits
    ber = (bit_errors / total_bits) * 100 # (ค่า BER เป็นเปอร์เซ็นต์)

    # ผิดพลาดได้ไม่เกิน 10%
    match_threshold = 10.0
    is_match = bool(ber <= match_threshold)


    return jsonify({
        "success": True,
        "bit_errors": int(bit_errors),
        "total_bits": int(total_bits),
        "ber": round(ber, 2), # ทศนิยม 2 ตำแหน่ง
        "is_match": is_match,
        "message": f"Watermark verified. BER: {ber:.2f}%"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)