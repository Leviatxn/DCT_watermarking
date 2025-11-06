import React, { useState } from "react";
import Swal from "sweetalert2";
import axios from "axios";
import "./App.css";

export default function App() {
  const [host, setHost] = useState(null);
  const [watermark, setWatermark] = useState(null);
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState("embed");

  // ✅ state ใหม่สำหรับ preview
  const [previewHost, setPreviewHost] = useState(null);
  const [previewWatermark, setPreviewWatermark] = useState(null);

  const handleHostChange = (e) => {
    const file = e.target.files[0];
    setHost(file);
    if (file) setPreviewHost(URL.createObjectURL(file));
  };

  const handleWatermarkChange = (e) => {
    const file = e.target.files[0];
    setWatermark(file);
    if (file) setPreviewWatermark(URL.createObjectURL(file));
  };

  const handleEmbed = async () => {
    if (!host || !watermark) return alert("กรุณาเลือกรูปทั้งสองไฟล์ก่อน!");
    const formData = new FormData();
    formData.append("image", host);
    formData.append("watermark", watermark);
    const res = await axios.post("http://localhost:5000/embed", formData, {
      responseType: "blob",
    });
    setResult(URL.createObjectURL(res.data));

    Swal.fire({
      title: "ฝังลายน้ำสำเร็จ!",
      html: `<img src="${URL.createObjectURL(res.data)}" style="width:100%;border-radius:10px"/>`,
      confirmButtonText: "ปิด",
      confirmButtonColor: "#3085d6",
    });
  };

  const handleExtract = async () => {
    if (!host) return alert("กรุณาเลือกรูปที่จะตรวจสอบก่อน!");
    const formData = new FormData();
    formData.append("image", host);
    const res = await axios.post("http://localhost:5000/extract", formData, {
      responseType: "blob",
    });
    setResult(URL.createObjectURL(res.data));
  };

    const handleCloseResult = () => {
    setResult(null);
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = result;
    link.download =
      mode === "embed" ? "watermarked_image.png" : "extracted_watermark.png";
    link.click();
  };

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">🖼️ DCT Invisible Watermark Tool</h1>

        <div className="mode-toggle">
          <button
            className={mode === "embed" ? "active" : ""}
            onClick={() => setMode("embed")}
          >
            Embed Mode
          </button>
          <button
            className={mode === "extract" ? "active" : ""}
            onClick={() => setMode("extract")}
          >
            Extract Mode
          </button>
        </div>

        <div className="upload-section">
          <label>📷 เลือกรูปภาพหลัก:</label>
          <input type="file" accept="image/*" onChange={handleHostChange} />

          {/* ✅ แสดงภาพหลักเมื่ออัปโหลด */}
          {previewHost && (
            <img
              src={previewHost}
              alt="host-preview"
              className="preview"
              style={{ maxWidth: "100%", borderRadius: "10px" }}
            />
          )}

          {mode === "embed" && (
            <>
              <label>💧 เลือกรูปลายน้ำ:</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleWatermarkChange}
              />

              {/* ✅ แสดงภาพลายน้ำเมื่ออัปโหลด */}
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
            </>
          )}
        </div>

        <div className="button-section">
          {mode === "embed" ? (
            <button className="btn-primary" onClick={handleEmbed}>
              🔒 ฝังลายน้ำ
            </button>
          ) : (
            <button className="btn-primary" onClick={handleExtract}>
              🔍 ตรวจสอบลายน้ำ
            </button>
          )}
        </div>
      </div>
 {result && (
          <div className="result-section">
            <h3>ผลลัพธ์:</h3>
            <img
              src={result}
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
