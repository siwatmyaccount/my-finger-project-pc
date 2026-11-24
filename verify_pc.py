"""Check installed assets, models and audio decoding without opening a webcam."""
import io
import argparse
import base64
from pathlib import Path
import sys
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image
import pygame
import main as app
from pc_runtime import load_landmark_model, resource_path, open_camera, choose_camera_device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', action='store_true', help='Also read a live webcam frame (not saved).')
    args = parser.parse_args()
    print('Build:', app.BUILD)
    print('Python:', sys.version.split()[0])
    app.ensure_prompt_files()
    for _, _, name in app.PROMPT_WEIGHTS.values():
        assert (Path(app.FONT_DIR) / name).is_file(), name
    for pose in range(1, 6):
        with Image.open(resource_path('pictures', 'EX_POSE', f'pose{pose}.png')) as picture:
            picture.verify()
    model = load_landmark_model(Interpreter, 2)
    model_input = model.get_input_details()[0]
    model.set_tensor(model_input['index'], np.zeros(model_input['shape'], dtype=model_input['dtype']))
    model.invoke()
    for output in model.get_output_details():
        assert np.isfinite(model.get_tensor(output['index'])).all()
    detector = app.load_palm_detector(Interpreter, resource_path(), 2)
    assert detector is not None, 'Palm detector missing from task'
    tracker = app.StableLocalTracker(model, detector)
    assert tracker.handedness is not None, 'Hand-side output missing'
    # Real native inference on an empty image must not start the exercise timer.
    points, matched, _ = tracker.process(np.zeros((480, 640, 3), dtype=np.uint8), 1.0, 1, 'ซ้าย')
    assert points is None and not matched
    print('PASS: native palm/landmark models and empty-frame inference')
    if args.camera:
        capture = open_camera(choose_camera_device())
        try:
            ok, frame = capture.read()
            assert ok and frame is not None and frame.size
            print('PASS: live camera frame', frame.shape)
        finally:
            capture.release()
    # Decode MP3 files with SDL dummy output; this does not claim audible playback.
    import os
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    pygame.mixer.init()
    try:
        for number in range(1, 11):
            clip = pygame.mixer.Sound(resource_path('Voices', f'{number:03d}.mp3'))
            assert clip.get_length() > 0
        for content in app.ENGLISH_VOICE_CLIPS.values():
            clip = pygame.mixer.Sound(file=io.BytesIO(base64.b64decode(content)))
            assert clip.get_length() > 0
    finally:
        pygame.mixer.quit()
    assert app.web_report.qr_image('http://127.0.0.1:8080/report.html') is not None
    print('PASS: Thai/English audio decoding, QR generator, fonts and pose images')
    print('Hand-pose accuracy, audible speakers and phone Wi-Fi access still require a user check.')


if __name__ == '__main__':
    main()
