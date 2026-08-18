import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { api } from "../api";

const MAX_BYTES = 500 * 1024 * 1024;

export default function UploadStep({ onUploaded, onNext }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [err, setErr] = useState("");
  const [uploading, setUploading] = useState(false);
  const [pct, setPct] = useState(0);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "video/mp4": [".mp4"],
      "video/x-msvideo": [".avi"],
      "video/quicktime": [".mov"],
    },
    multiple: false,
    onDrop: (files) => {
      setErr("");
      const f = files?.[0];
      if (!f) return;
      if (f.size > MAX_BYTES) {
        setErr("File too large. Max 500MB.");
        return;
      }
      setFile(f);
      setPreviewUrl(URL.createObjectURL(f));
      setPct(0);
    },
  });

  async function upload() {
    if (!file) return;
    setUploading(true);
    setErr("");

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await api.post("/api/upload_video", form, {
        onUploadProgress: (e) => {
          if (!e.total) return;
          setPct(Math.round((e.loaded / e.total) * 100));
        },
      });

      // backend returns {video_id, path}
      onUploaded({ file, previewUrl, ...res.data });
      onNext();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function clear() {
    setFile(null);
    setPreviewUrl("");
    setErr("");
    setPct(0);
  }

  return (
    <div className="glass p-6 space-y-4">
      <div
        {...getRootProps()}
        className={[
          "border-2 border-dashed rounded-xl p-10 text-center cursor-pointer",
          isDragActive ? "border-blue-400 bg-white/5" : "border-white/20 bg-white/5",
        ].join(" ")}
      >
        <input {...getInputProps()} />
        <p className="text-lg font-semibold">
          {isDragActive ? "Drop the video here…" : "Drag & drop video or click to select"}
        </p>
        <p className="help mt-2">MP4 / AVI / MOV • Max 500MB</p>
      </div>

      {err && <p className="error">{err}</p>}

      {previewUrl && (
        <div className="border border-white/15 rounded-xl p-4 bg-white/5">
          <p className="font-semibold mb-2">Preview</p>
          <video src={previewUrl} controls className="w-full rounded-lg" />
        </div>
      )}

      {uploading && (
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span>Uploading…</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-white/10 rounded">
            <div className="h-2 bg-blue-500 rounded" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn-ghost" onClick={clear} disabled={!file || uploading}>
          Clear
        </button>
        <button className="btn-primary" onClick={upload} disabled={!file || uploading}>
          Upload & Next
        </button>
      </div>
    </div>
  );
}