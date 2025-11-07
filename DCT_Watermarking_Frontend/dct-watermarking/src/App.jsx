import React, { useState } from "react";
import Swal from "sweetalert2";
import axios from "axios";
import "./App.css";


export default function App() {
  // --- 1. เปลี่ยนชื่อ State เพื่อความชัดเจน ---
  const [host, setHost] = useState(null);
  const [watermark, setWatermark] = useState(null);
  // 'embedResult' จะเก็บ URL ของ "ภาพ" ที่ฝังลายน้ำแล้ว
  const [embedResult, setEmbedResult] = useState(null); 
  const [mode, setMode] = useState("embed");

  const [previewHost, setPreviewHost] = useState(null);
  const [previewWatermark, setPreviewWatermark] = useState(null);
  
  // (เราไม่ต้องการ state 'extractResult' เพราะเราจะแสดงใน popup)

  const clearInputs = () => {
    setHost(null);
    setWatermark(null);
    setPreviewHost(null);
    setPreviewWatermark(null);
    setEmbedResult(null);
    // เคลียร์ค่าใน input element ด้วย
    document.querySelectorAll('input[type="file"]').forEach(input => input.value = '');
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    clearInputs(); // เคลียร์ทุกอย่างเมื่อเปลี่ยนโหมด
  };

  const handleHostChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setHost(file);
    setPreviewHost(URL.createObjectURL(file));
  };

  const handleWatermarkChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setWatermark(file);
    setPreviewWatermark(URL.createObjectURL(file));
  };

  const handleEmbed = async () => {
    if (!host || !watermark) return Swal.fire("⚠️ แจ้งเตือน", "กรุณาเลือกรูปทั้งสองไฟล์ก่อน!", "warning");
    
    const formData = new FormData();
    formData.append("image", host);
    formData.append("watermark", watermark);

    try {
      const res = await axios.post("http://localhost:5000/embed", formData, {
        responseType: "blob", // Embed ยังคง trả về "blob" (ภาพ)
      });
      
      const imageUrl = URL.createObjectURL(res.data);
      setEmbedResult(imageUrl); // เก็บผลลัพธ์ที่เป็นภาพไว้ใน state

      Swal.fire({
        title: "✅ ฝังลายน้ำสำเร็จ!",
        html: `<img src="${imageUrl}" style="width:100%;border-radius:10px" alt="watermarked output"/>`,
        showConfirmButton: true,
        confirmButtonText: "ปิด",
        confirmButtonColor: "#  3085d6",
        customClass: {
          popup: "swal2-animate",
          title: "swal2-font",
          htmlContainer: "swal2-font",
        },
      });
    } catch (err) {
      console.error(err);
      Swal.fire("เกิดข้อผิดพลาด!", "ไม่สามารถฝังลายน้ำได้", "error");
    }
  };

  // --- 2. แก้ไข handleExtract ทั้งหมด ---
  const handleExtract = async () => {

    if (!host || !watermark)
      return Swal.fire({
        title: "⚠️ แจ้งเตือน",
        text: "กรุณาเลือกรูปภาพและลายน้ำต้นฉบับ!",
        icon: "warning",
        confirmButtonText: "ตกลง",
        confirmButtonColor: "#3085d6",
        customClass: {
          popup: "swal2-animate",
          title: "swal2-font",
          htmlContainer: "swal2-font",
        },
      });

    const formData = new FormData();
    formData.append("image", host);

    formData.append("original_watermark", watermark); 

    try {
      const res = await axios.post("http://localhost:5000/extract", formData);
      
      const data = res.data;

      const resultColor = data.is_match ? "#4CAF50" : "#F44336";
      const resultText = data.is_match ? "ลายน้ำตรงกัน" : "ลายน้ำไม่ตรงกัน";

      
      Swal.fire({
        title: "🔍 ผลการตรวจสอบ",
        icon: data.is_match ? "success" : "error",
        html: `
          <div style="text-align:left;line-height:1.6;padding:30px;">
            <p className:"swal2-font" style="font-size:1.2em;font-weight:bold;color:${resultColor};">
              สถานะ: ${resultText}
            </p>
            <hr>
            <p><strong>Bit Error Rate (BER):</strong> ${data.ber}%</p>
            <p><strong>จำนวนบิตที่ผิดพลาด:</strong> ${data.bit_errors} / ${data.total_bits} บิต</p>
          </div>
        `,
        confirmButtonText: "ปิด",
        confirmButtonColor: "#3085d6",
        background: "#fefefe",
        customClass: {
          popup: "swal2-animate",
          title: "swal2-font",
          htmlContainer: "swal2-font",
        },
      });
    } catch (err) {
      console.error("Error during extraction:", err);
      Swal.fire("เกิดข้อผิดพลาด!", "ไม่สามารถตรวจสอบลายน้ำได้", "error");
    }
           
  };

  // --- 3. แก้ไขฟังก์ชันที่เกี่ยวข้องกับผลลัพธ์ ---
  const handleCloseResult = () => {
    setEmbedResult(null); // ปิดผลลัพธ์ของ embed
    clearInputs();
  };

  const handleDownload = () => {
    if (!embedResult) return;
    const link = document.createElement("a");
    link.href = embedResult;
    link.download = "watermarked_image.png"; // Extract ไม่มีดาวน์โหลด
    link.click();
  };

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">🖼️ DCT Watermark Verification</h1>

        <div className="mode-toggle">
          <button
            className={mode === "embed" ? "active" : ""}
            onClick={() => handleModeChange("embed")}
          >
            โหมดฝังลายน้ำ (Embed)
          </button>
          <button
            className={mode === "extract" ? "active" : ""}
            onClick={() => handleModeChange("extract")}
          >
            โหมดตรวจสอบ (Extract)
          </button>
        </div>

        <div className="upload-section">

          <label>
            📷 
            {mode === "embed" ? " เลือกรูปภาพหลัก (Host):" : " เลือกรูปภาพที่จะตรวจสอบ:"}
          </label>
          <input type="file" accept="image/*" onChange={handleHostChange} />

          {previewHost && (
            <img
              src={previewHost}
              alt="host-preview"
              className="preview"
              style={{ maxWidth: "100%", borderRadius: "10px" }}
            />
          )}

          
          <label>
            💧 
            {mode === "embed" ? " เลือกรูปลายน้ำ (Watermark):" : " เลือกลายน้ำต้นฉบับ (Original):"}
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleWatermarkChange}
          />

          {previewWatermark && (
            <img
              src={previewWatermark}
              alt="watermark-preview"
              className="preview"
              style={{
                maxWidth: "150px",
                borderRadius: "8px",
                opacity: 0.8,
                border: "1px solid #ccc",
                marginTop: "8px",
              }}
            />
          )}
        </div>

        <div className="button-section">
          {mode === "embed" ? (
            <button className="btn-primary" onClick={handleEmbed} disabled={!host || !watermark}>
              🔒 ฝังลายน้ำ
            </button>
          ) : (
            <button className="btn-primary" onClick={handleExtract} disabled={!host || !watermark}>
              🔍 ตรวจสอบลายน้ำ
            </button>
          )}
        </div>
      </div>
        {mode === "embed" && embedResult && (
          <div className="card" style={{marginLeft:'20px'}}>
          <div className="result-section">
            <h3>ผลลัพธ์ (ภาพที่ฝังลายน้ำ):</h3>
            <img
              src={embedResult}
              alt="Result"
              className="preview"
              style={{ maxWidth: "100%", borderRadius: "10px", marginTop: "10px" }}
            />
            <div style={{ display: "flex", gap: "10px", justifyContent: "center", marginTop: "10px" }}>
              <button className="btn-secondary" onClick={handleCloseResult}>
                ❌ ปิดผลลัพธ์
              </button>
              <button className="btn-success" onClick={handleDownload}>
                ⬇️ ดาวน์โหลด
              </button>
            </div>
          </div>
          </div>
        )}

    </div>
  );
}