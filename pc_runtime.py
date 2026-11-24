"""Windows services for the v28 UI; no Tk calls or import-time device access."""
import base64
import io
import logging
import os
from pathlib import Path
import sys
import time
import zipfile


def resource_path(*parts):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(root.joinpath(*parts))


def data_path(*parts):
    override = os.environ.get("ANTI_FINGER_DATA_DIR")
    if override:
        root = Path(override).expanduser().resolve()
    elif getattr(sys, "frozen", False):
        root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AntiTriggerFingersPC" / "v28"
    else:
        root = Path(__file__).resolve().parent / "data" / "v28"
    root.mkdir(parents=True, exist_ok=True)
    return str(root.joinpath(*parts))


def choose_camera_device():
    value = os.environ.get("CAMERA_DEVICE", "").strip()
    if not value:
        return None  # probe camera indexes; never pass /dev/video* to Windows
    if not value.isdecimal():
        raise ValueError("CAMERA_DEVICE must be a Windows camera index, e.g. 0 or 1")
    return int(value)


def open_camera(device=None, stop_event=None, cv=None):
    if cv is None:
        import cv2 as cv
    backends = (cv.CAP_DSHOW, cv.CAP_MSMF) if sys.platform == "win32" else (cv.CAP_ANY,)
    devices = range(4) if device is None else (device,)
    for index in devices:
        for backend in backends:
            if stop_event is not None and stop_event.is_set():
                raise RuntimeError("Camera opening cancelled")
            cap = cv.VideoCapture(index, backend)
            try:
                if cap.isOpened():
                    cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
                    ok, frame = cap.read()
                    if ok and frame is not None and frame.size:
                        logging.info("Camera index=%s backend=%s", index, cap.getBackendName())
                        return cap
            except Exception:
                logging.exception("Camera index=%s backend=%s failed", index, backend)
            cap.release()
    raise RuntimeError("Cannot read a webcam. Check Windows camera permissions and close other camera apps.")


def load_landmark_model(factory, threads):
    """The existing task archive contains the same handedness model used by Pi v28."""
    with zipfile.ZipFile(resource_path("hand_landmarker.task")) as bundle:
        content = bundle.read("hand_landmarks_detector.tflite")
    model = factory(model_content=content, num_threads=threads)
    model.allocate_tensors()
    return model


def play_voice_requests(app, english_clips, mixer=None):
    """One mixer owner; deferred pose prompts do not interrupt the start clip."""
    if mixer is None:
        from pygame import mixer
    channel = None
    try:
        while True:
            with app._voice_condition:
                app._voice_condition.wait_for(lambda: app._voice_pending or app._voice_stopping)
                if app._voice_stopping:
                    return
                filename, language, revision, wait = app._voice_pending
                app._voice_pending = None
            if wait and channel is not None:
                deadline = time.monotonic() + 30
                while channel.get_busy() and time.monotonic() < deadline:
                    with app._voice_condition:
                        if app._voice_stopping:
                            return
                        if revision != app._voice_revision:
                            break
                        app._voice_condition.wait(.03)
            with app._voice_condition:
                if app._voice_stopping:
                    return
                if revision != app._voice_revision:
                    continue
            try:
                if channel is not None:
                    channel.stop()
                if filename is None:
                    continue
                if not mixer.get_init():
                    mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                if language == "en":
                    sound = mixer.Sound(file=io.BytesIO(base64.b64decode(english_clips[filename])))
                else:
                    sound = mixer.Sound(resource_path("Voices", filename))
                channel = mixer.Channel(0)
                channel.play(sound)
            except Exception:
                logging.exception("Voice playback failed: %s (%s)", filename, language)
    finally:
        if channel is not None:
            channel.stop()
        if mixer.get_init():
            mixer.quit()
