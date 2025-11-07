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
    if (!host || !watermark) return alert("กรุณาเลือกรูปทั้งสองไฟล์ก่อน!");
    
    const formData = new FormData();
    formData.append("image", host);
    formData.append("watermark", watermark);

    try {
      const res = await axios.post("http://localhost:5000/embed", formData, {
        responseType: "blob", // Embed ยังคง trả về "blob" (ภาพ)
      });
      
      const imageUrl = URL.createObjectURL(res.data);
      setEmbedResult(imageUrl); // เก็บผลลัพธ์ที่เป็นภาพไว้ใน state

      // เรียกใช้ 'window.Swal' แทน 'Swal'
      if (window.Swal) {
        window.Swal.fire({
          title: "ฝังลายน้ำสำเร็จ!",
          html: `<img src="${imageUrl}" style="width:100%;border-radius:10px" alt="watermarked output"/>`,
          confirmButtonText: "ปิด",
          confirmButtonColor: "#3085d6",
        });
      } else {
        alert("ฝังลายน้ำสำเร็จ!"); // Fallback
      }
    } catch (err) {
      console.error(err);
      if (window.Swal) {
        window.Swal.fire("เกิดข้อผิดพลาด!", "ไม่สามารถฝังลายน้ำได้", "error");
      } else {
        alert("เกิดข้อผิดพลาด! ไม่สามารถฝังลายน้ำได้");
      }
    }
  };

  // --- 2. แก้ไข handleExtract ทั้งหมด ---
  const handleExtract = async () => {

    if (!host || !watermark) {
      return alert("กรุณาเลือกรูปภาพที่จะตรวจสอบ และรูปลายน้ำต้นฉบับ!");
    }

    const formData = new FormData();
    formData.append("image", host);

    formData.append("original_watermark", watermark); 

    try {
      const res = await axios.post("http://localhost:5000/extract", formData);
      
      const data = res.data;

      const resultColor = data.is_match ? "#4CAF50" : "#F44336";
      const resultText = data.is_match ? "ลายน้ำตรงกัน" : "ลายน้ำไม่ตรงกัน";

      if (window.Swal) {
        window.Swal.fire({
          title: "ผลการตรวจสอบ!",
          icon: data.is_match ? "success" : "error",
          html: `
            <div style="text-align: left; padding: 0 1em;">
              <p style="font-size: 1.2em; color: ${resultColor}; font-weight: bold;">
                สถานะ: ${resultText}
              </p>
              <hr>
              <p><strong>Bit Error Rate (BER):</strong> ${data.ber}%</p>
              <p><strong>จำนวนบิตที่ผิดพลาด:</strong> ${data.bit_errors} / ${data.total_bits} บิต</p>
            </div>
          `,
          confirmButtonText: "ปิด",
          confirmButtonColor: "#3085d6",
        });
      } else {
        // Fallback
        alert(`ผลการตรวจสอบ: ${resultText}\nBER: ${data.ber}% (${data.bit_errors}/${data.total_bits} บิต)`);
      }

    } catch (err) {
      console.error("Error during extraction:", err);
      if (window.Swal) {
        window.Swal.fire("เกิดข้อผิดพลาด!", "ไม่สามารถตรวจสอบลายน้ำได้", "error");
      } else {
        alert("เกิดข้อผิดพลาด! ไม่สามารถตรวจสอบลายน้ำได้");
      }
    }
  };

  // --- 3. แก้ไขฟังก์ชันที่เกี่ยวข้องกับผลลัพธ์ ---
  const handleCloseResult = () => {
    setEmbedResult(null); // ปิดผลลัพธ์ของ embed
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
      {/* คุณสามารถเพิ่ม CSS ที่นี่ได้ถ้าจำเป็น
        <style>
        {`
          .app-container { ... }
          .card { ... }
        `}
        </style> 
      */}
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
          
          {/* --- 4. เปลี่ยน Label ตามโหมด --- */}
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

          {/* --- 5. แสดงช่องอัปโหลดลายน้ำทั้งสองโหมด --- */}
          {/* (เพราะ Extract ก็ต้องใช้ลายน้ำต้นฉบับ) */}
          
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
      
      {/* --- 6. แก้ไขส่วนแสดงผลลัพธ์ --- */}
      {/* ส่วนนี้จะแสดงเฉพาะผลลัพธ์ของ "Embed" (ที่เป็นภาพ) เท่านั้น */}
      {/* ผลลัพธ์ของ "Extract" จะแสดงใน SweetAlert popup */}
      {mode === "embed" && embedResult && (
        <div className="result-section">
          <h3>ผลลัพธ์ (ภาพที่ฝังลายน้ำ):</h3>
          <img
            src={embedResult}
            alt="Result"
            className="preview"
            style={{
              maxWidth: "100%",
              borderRadius: "10px",
              marginTop: "10px",
            }}
          />
          <div
            style={{
              display: "flex",
              gap: "10px",
              justifyContent: "center",
              marginTop: "10px",
            }}
          >
            <button className="btn-secondary" onClick={handleCloseResult}>
              ❌ ปิดผลลัพธ์
            </button>
            <button className="btn-success" onClick={handleDownload}>
              ⬇️ ดาวน์โหลด
            </button>
          </div>
        </div>
      )}
    </div>
  );
}