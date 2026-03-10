import time
import threading
import cv2


class CameraWorker:
    def __init__(self, source_type: str = "device", source_value=None):
        self.source_type = source_type   # "device" | "rtsp"
        self.source_value = source_value # índice int o url str

        self.cap = None
        self.running = False
        self.thread = None

        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_ok_at = 0.0

    def _open_capture(self):
        if self.source_type == "device":
            return cv2.VideoCapture(int(self.source_value), cv2.CAP_DSHOW)

        if self.source_type == "rtsp":
            return cv2.VideoCapture(str(self.source_value), cv2.CAP_FFMPEG)

        raise ValueError(f"Tipo de fuente no soportado: {self.source_type}")

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                try:
                    if self.cap is not None:
                        self.cap.release()
                except Exception:
                    pass

                self.cap = self._open_capture()
                time.sleep(0.3)

                if not self.cap.isOpened():
                    time.sleep(0.7)
                    continue

            try:
                ok, frame = self.cap.read()
            except cv2.error:
                ok, frame = False, None

            if not ok or frame is None:
                time.sleep(0.03)
                continue

            with self.lock:
                self.latest_frame = frame.copy()
                self.last_ok_at = time.time()

        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def stop(self):
        self.running = False


CAMERA_WORKERS = {}


def get_camera_worker(cam_id: str, source: dict) -> CameraWorker:
    worker = CAMERA_WORKERS.get(cam_id)

    source_type = source.get("type")
    source_value = source.get("index") if source_type == "device" else source.get("url")

    if worker is None:
        worker = CameraWorker(source_type=source_type, source_value=source_value)
        CAMERA_WORKERS[cam_id] = worker
        worker.start()
        return worker

    # si cambió la config de la cámara, recrearlo
    if worker.source_type != source_type or worker.source_value != source_value:
        try:
            worker.stop()
        except Exception:
            pass

        worker = CameraWorker(source_type=source_type, source_value=source_value)
        CAMERA_WORKERS[cam_id] = worker
        worker.start()

    elif not worker.running:
        worker.start()

    return worker
