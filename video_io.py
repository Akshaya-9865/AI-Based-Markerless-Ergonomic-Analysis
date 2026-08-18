import cv2

def probe_video(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return {"fps": fps, "width": w, "height": h, "frames": n}

def iter_frames(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video.")
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        yield i, frame
        i += 1
    cap.release()
