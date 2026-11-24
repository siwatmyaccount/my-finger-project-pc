import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.request import urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as app
import pc_runtime
import web_report


def state_object():
    state = SimpleNamespace(
        completed_sets=[], round=1, current_pose=3, set=0, time_max=5,
        _set_stable_poses=6, _pain_before=4, _pain_after=2, _last_pain=2,
        _report_started_at=datetime.now().astimezone(),
        target_hand_var=Mock(get=lambda: 'ขวา'), target_sets_var=Mock(get=lambda: 1),
        _daily_pose_counts=[(datetime.now().date(), 7)], draw_five_day_trend=Mock(),
        POSE_CUES=app.AntiTriggerFingersApp.POSE_CUES,
        _pose_had_long_pause=False,
    )
    for name in ('_report_state_path', '_clear_report_storage', '_save_report_state',
                 '_load_report_state', '_web_report_data', '_practice_tips', 'short_advice'):
        setattr(state, name, MethodType(getattr(app.AntiTriggerFingersApp, name), state))
    return state


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'ANTI_FINGER_DATA_DIR': self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_resume_partial_progress_and_pain(self):
        state = state_object()
        state._save_report_state()
        resumed = state_object()
        resumed._pain_before = resumed._pain_after = None
        resumed._load_report_state()
        self.assertEqual(resumed._saved_progress, {'round': 1, 'pose': 3, 'stable_poses': 6, 'hand': 'ขวา'})
        self.assertEqual((resumed._pain_before, resumed._pain_after), (4, 2))

    def test_clear_only_touches_v28_data(self):
        legacy = Path(self.temp.name) / 'legacy'
        legacy.mkdir()
        legacy_file = legacy / 'Anti-Finger.txt'
        legacy_file.write_text('previous PC history', encoding='utf-8')
        state = state_object()
        state._save_report_state()
        state._clear_report_storage()
        self.assertFalse(Path(state._report_state_path()).exists())
        self.assertEqual(legacy_file.read_text(encoding='utf-8'), 'previous PC history')

    def test_expired_progress_is_not_resumed(self):
        state = state_object()
        state._report_started_at -= timedelta(days=6)
        state._save_report_state()
        resumed = state_object()
        resumed._load_report_state()
        self.assertFalse(hasattr(resumed, '_saved_progress'))

    def test_partial_report_counts_actual_poses_and_escapes_text(self):
        data = state_object()._web_report_data()
        self.assertEqual(data['simple']['poses'], 7)
        self.assertEqual(data['simple']['sets'], 0)
        self.assertEqual(len(data['sets']), 1)
        data['text']['title'] = '<script>bad()</script>'
        rendered = web_report.render_report(data)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_report_http_and_path_restrictions(self):
        state = state_object()
        name = web_report.save_report(self.temp.name, state._web_report_data(), '2026-11-24_20-00-00')
        server = web_report.ReportServer(self.temp.name, port=0, host='127.0.0.1')
        server.start()
        base = f'http://127.0.0.1:{server.port}'
        try:
            with urlopen(base + '/' + name, timeout=3) as reply:
                self.assertEqual(reply.status, 200)
                self.assertIn('7'.encode(), reply.read())
            with urlopen(base + '/latest', timeout=3) as reply:
                self.assertTrue(reply.url.endswith(name))
            for target in ('/../main.py', '/report_state.json', '/fonts/../../main.py'):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(base + target, timeout=3)
                self.assertEqual(raised.exception.code, 404)
        finally:
            server.stop()
        self.assertFalse(server._thread.is_alive())

    def test_gate_requires_new_frames_and_rejects_stale_or_changed_hand(self):
        gate = app.PoseHoldGate()
        context = (1, 'ซ้าย')
        self.assertFalse(gate.update(1, 1, 1, True, True, True, context)[0])
        self.assertFalse(gate.update(1.2, 1, 1, True, True, True, context)[0])
        self.assertTrue(gate.update(1.21, 2, 1.21, True, True, True, context)[0])
        self.assertFalse(gate.update(1.22, 3, 1.22, True, True, True, (1, 'ขวา'))[0])
        self.assertFalse(gate.update(3, 3, 1.22, True, True, True, (1, 'ขวา'))[0])

    def test_complete_set_saves_and_prepares_next_set(self):
        state = state_object()
        state.round, state.current_pose = 2, 5
        state._pose_had_long_pause = False
        state._pose_pause_started = None
        state.pose_name = ['', '1', '2', '3', '4', '5']
        state.green_btn = state.hover_green_bt = 'green'
        state.start_stop_button = Mock()
        state.main_content_frame = Mock()
        for name in ('write_log', 'set_feedback', 'set_breathing', 'record_completed_set',
                     '_start_label', 'trigger_goal_popup', 'update_round', 'timer_reset',
                     'update_EX_pose', 'update_text', 'after', 'reset_feedback', '_queue_voice'):
            setattr(state, name, Mock())
        app.AntiTriggerFingersApp._on_pose_success(state)
        self.assertEqual((state.set, state.round, state.current_pose), (1, 0, 1))
        self.assertFalse(state.running)
        state.record_completed_set.assert_called_once()
        persisted = json.loads(Path(state._report_state_path()).read_text(encoding='utf-8'))
        self.assertEqual(persisted['progress']['pose'], 1)


class VoiceTests(unittest.TestCase):
    def test_deferred_pose_does_not_cut_start_and_pause_interrupts(self):
        state = SimpleNamespace(_voice_condition=threading.Condition(), _voice_pending=None,
                                _voice_stopping=False, _voice_revision=0)
        state._queue_voice = MethodType(app.AntiTriggerFingersApp._queue_voice, state)
        played = []
        start_played, next_played = threading.Event(), threading.Event()
        mixer = Mock()
        mixer.get_init.return_value = True
        mixer.Sound.side_effect = lambda path: Path(path).name
        channel = mixer.Channel.return_value
        channel.get_busy.return_value = True
        def play(clip):
            played.append(clip)
            (start_played if len(played) == 1 else next_played).set()
        channel.play.side_effect = play
        worker = threading.Thread(target=pc_runtime.play_voice_requests,
                                  args=(state, {}, mixer), daemon=True)
        worker.start()
        try:
            state._queue_voice('006.mp3')
            self.assertTrue(start_played.wait(2))
            state._queue_voice('001.mp3', wait=True)
            self.assertFalse(next_played.wait(.15))
            state._queue_voice('007.mp3')
            self.assertTrue(next_played.wait(2))
            self.assertEqual(played, ['006.mp3', '007.mp3'])
            next_played.clear()
            state._queue_voice('001.mp3', wait=True)
            self.assertFalse(next_played.wait(.1))
            channel.get_busy.return_value = False
            self.assertTrue(next_played.wait(2))
            self.assertEqual(played, ['006.mp3', '007.mp3', '001.mp3'])
        finally:
            with state._voice_condition:
                state._voice_stopping = True
                state._voice_condition.notify_all()
            worker.join(2)
        self.assertFalse(worker.is_alive())
        mixer.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
