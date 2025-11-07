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
      title: "🔒 EMBED SUCCESS! ✅ ",
      html: `<img src="${URL.createObjectURL(res.data)}" style="width:100%;border-radius:10px"/>`,
      confirmButtonText: "❌CLOSE❌",
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
    {/* 🔹 Navbar ด้านบน */}
    <nav className="navbar">
      <h1 className="navbar-title">🖼️ DCT Invisible Watermark Tool</h1>

      <div className="mode-toggle">
        <button
          className={mode === "embed" ? "active" : ""}
          onClick={() => setMode("embed")}
        >
         🔒 Embed Mode
        </button>
        <button
          className={mode === "extract" ? "active" : ""}
          onClick={() => setMode("extract")}
        >
          🔍 Extract Mode
        </button>
      </div>
    </nav>

    {/* 🔹 ส่วนล่าง: กล่องซ้าย-ขวา */}
    <div className="content-wrapper">
      {/* ซ้าย: อัปโหลด */}
      <div className="card">
        <div className="upload-section">
          <label>📷 Select Your Image 📷
          
          <input type="file" accept="image/*" onChange={handleHostChange} />
          </label>
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
              <label>💧 Select Your Watermark 💧 
              <input
                type="file"
                accept="image/*"
                onChange={handleWatermarkChange}
              />
              </label>
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
              🔒 DCT Embed 🔒
            </button>
          ) : (
            <button className="btn-primary" onClick={handleExtract}>
              🔍 DCT Extract 🔍
            </button>
          )}
        </div>
      </div>

      {/* ขวา: ผลลัพธ์ */}
      {result && (
        <div className="card">
          <h3>🏆 Result 🏆</h3>
          <div className="result-section">
            
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
            </div>
            <div
              style={{
                display: "flex",
                gap: "10px",
                justifyContent: "center",
                marginTop: "10px",
              }}
            >
              <button className="btn-secondary" onClick={handleCloseResult}>
                ❌ CLOSE
              </button>
              <button className="btn-success" onClick={handleDownload}>
                ⬇️ DOWNLOAD
              </button>
            </div>
          </div>
        
      )}
    </div>
  </div>
);


}