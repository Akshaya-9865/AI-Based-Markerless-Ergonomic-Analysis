import { useEffect, useRef, useState } from "react";

export default function VideoPlayer({ src }) {
  const videoRef = useRef(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
  }, [src]);

  if (!src) return null;

  return (
    <div className="rounded-xl overflow-hidden border border-white/15 bg-black">
      <video
        ref={videoRef}
        src={src}
        controls
        className="w-full rounded-xl"
        style={{ maxHeight: "480px" }}
        onError={() => setError(true)}
      >
        Your browser does not support the video tag.
      </video>
      {error && (
        <p className="text-red-300 text-sm p-3">
          Could not load video. Try opening in a new tab instead.
        </p>
      )}
    </div>
  );
}