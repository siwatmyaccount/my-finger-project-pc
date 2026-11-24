"""Real Tk smoke test using temporary records; no webcam or audible playback."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import patch
from contextlib import nullcontext

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--live-camera', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='finger-pc-gui-') as folder:
        os.environ['ANTI_FINGER_DATA_DIR'] = folder
        os.environ.pop('ANTI_FINGER_LAUNCHER', None)
        import main as app
        app.ctk.set_widget_scaling(1.0)
        app.ctk.set_window_scaling(1.0)
        assert app.register_prompt_fonts() == 4, 'Windows font registration failed'
        errors = []
        video_patch = (nullcontext() if args.live_camera else
                       patch.object(app.AntiTriggerFingersApp, '_start_video', lambda self: None))
        with video_patch, \
             patch.object(app.AntiTriggerFingersApp, '_voice_loop', lambda self: None):
            window = app.AntiTriggerFingersApp()
        def callback_error(*exc):
            errors.append(''.join(traceback.format_exception(*exc)))
        window.report_callback_exception = callback_error
        def initial_check():
            assert app._PROMPT_READY, 'Prompt TH unavailable to Tk'
            window.toggle_start_pause()
            assert window.countdown_active
            window.toggle_start_pause()
            assert not window.countdown_active and not window.running
            window.pain_var.set(3)
            window.save_pain_log()
            for _ in range(15):
                window._on_pose_success()
            assert window.set == 1 and len(window.completed_sets) == 1

        def save_after():
            window.pain_pick_var.set(1)
            window.save_after_pain_from_report()

        def export():
            window._web_server.host = '127.0.0.1'
            window._web_server.port = 0
            window.export_completed_sets()
            assert window._qr_popup.winfo_exists()

        def finish():
            if args.live_camera:
                assert window.latest_frame is not None and window.frame_seq > 0, window.camera_error
                assert window.result_seq >= 0 and window.ai_error is None, window.ai_error
                print('PASS: live webcam -> v28 inference -> Tk preview', flush=True)
            saved = json.loads(Path(folder, 'report_state.json').read_text(encoding='utf-8'))
            assert len(saved['completed_sets']) == 1
            assert (saved['pain_before'], saved['pain_after']) == (3, 1)
            window.show_main_page()
            window.title('Anti-Trigger Fingers PC v28 - TEST DATA')
            print('PASS: Tk startup, fonts, start/pause, 15 poses, pain, language, advice, QR export', flush=True)
            window.after(300000 if args.interactive else 800, window.on_close)

        # Give Windows a paint/event cycle between opening and destroying dialogs.
        stages = iter([initial_check, window.show_history_page, save_after,
                       window.toggle_language, window.toggle_language, window.show_next_advice,
                       lambda: window.advice_popup.destroy(), export,
                       lambda: window._qr_popup.destroy(), finish])
        def check():
            try:
                stage = next(stages)
            except StopIteration:
                return
            try:
                print('GUI stage:', stage.__name__, flush=True)
                stage()
            except Exception:
                errors.append(traceback.format_exc())
            if errors:
                print('\n'.join(errors), flush=True)
                window.after(500, window.on_close)
            else:
                window.after(700, check)
        window.after(800, check)
        window.mainloop()
        assert window.exit_code == 0
        if errors:
            raise AssertionError('\n'.join(errors))
        print('PASS: clean shutdown; temporary records removed', flush=True)


if __name__ == '__main__':
    main()
