import time
import threading
import cv2


class CameraWorker:
    def __init__(self, sources: list[dict]):
        """
        sources: lista de fuentes en orden de prioridad.
        """
        self.sources = sources
        self.current_source_index = 0
        self.current_source = None

        self.cap = None
        self.running = False
        self.thread = None

        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_ok_at = 0.0

    def _open_capture(self, source: dict):
        source_type = source.get("type")

        if source_type == "device":
            return cv2.VideoCapture(int(source.get("index", 0)), cv2.CAP_DSHOW)

        if source_type == "rtsp":
            return cv2.VideoCapture(str(source.get("url")), cv2.CAP_FFMPEG)

        if source_type == "http":
            return cv2.VideoCapture(str(source.get("url")))

        raise ValueError(f"Tipo de fuente no soportado: {source_type}")

    def _try_open_any_source(self):
        total = len(self.sources)

        for i in range(total):
            idx = (self.current_source_index + i) % total
            source = self.sources[idx]

            try:
                cap = self._open_capture(source)
                time.sleep(0.2)

                if cap is not None and cap.isOpened():
                    self.current_source_index = idx
                    self.current_source = source

                    try:
                        if self.cap is not None:
                            self.cap.release()
                    except Exception:
                        pass

                    self.cap = cap
                    print(f"[INFO] Fuente activa: {source.get('name', 'unknown')}")
                    return True

                if cap is not None:
                    cap.release()

            except Exception as e:
                print(f"[WARN] No se pudo abrir fuente {source.get('name')}: {e}")

        self.current_source = None
        self.cap = None
        return False

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        fail_count = 0

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                ok = self._try_open_any_source()
                if not ok:
                    time.sleep(1.0)
                    continue

            try:
                ok, frame = self.cap.read()
            except cv2.error:
                ok, frame = False, None

            if not ok or frame is None:
                fail_count += 1
                time.sleep(0.05)

                # tras varios fallos seguidos, intenta cambiar de fuente
                if fail_count >= 20:
                    print("[WARN] Fallos consecutivos. Intentando otra fuente...")
                    try:
                        if self.cap is not None:
                            self.cap.release()
                    except Exception:
                        pass
                    self.cap = None
                    fail_count = 0

                continue

            fail_count = 0

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

    def get_active_source_name(self):
        if not self.current_source:
            return None
        return self.current_source.get("name")

    def switch_to_source(self, source_name: str):
        for idx, source in enumerate(self.sources):
            if source.get("name") == source_name:
                self.current_source_index = idx
                try:
                    if self.cap is not None:
                        self.cap.release()
                except Exception:
                    pass
                self.cap = None
                print(f"[INFO] Cambio manual a fuente: {source_name}")
                return True
        return False

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.5)


CAMERA_WORKERS = {}


def get_camera_worker(cam_id: str, sources: list[dict]) -> CameraWorker:
    worker = CAMERA_WORKERS.get(cam_id)

    if worker is None:
        worker = CameraWorker(sources=sources)
        CAMERA_WORKERS[cam_id] = worker
        worker.start()
        return worker

    if worker.sources != sources:
        try:
            worker.stop()
        except Exception:
            pass

        worker = CameraWorker(sources=sources)
        CAMERA_WORKERS[cam_id] = worker
        worker.start()

    elif not worker.running:
        worker.start()

    return worker
