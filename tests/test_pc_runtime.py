import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pc_runtime


class RuntimeTests(unittest.TestCase):
    def test_windows_camera_setting_is_index(self):
        with patch.dict(os.environ, {"CAMERA_DEVICE": "2"}):
            self.assertEqual(pc_runtime.choose_camera_device(), 2)
        with patch.dict(os.environ, {"CAMERA_DEVICE": ""}):
            self.assertIsNone(pc_runtime.choose_camera_device())
        with patch.dict(os.environ, {"CAMERA_DEVICE": "/dev/video0"}):
            with self.assertRaises(ValueError):
                pc_runtime.choose_camera_device()

    def test_camera_falls_back_and_releases_unreadable_device(self):
        cv = Mock(CAP_DSHOW=700, CAP_MSMF=1400, CAP_ANY=0)
        bad, good = Mock(), Mock()
        bad.read.return_value = (False, None)
        good.read.return_value = (True, Mock(size=100))
        cv.VideoCapture.side_effect = [bad, good]
        with patch.object(sys, "platform", "win32"):
            self.assertIs(pc_runtime.open_camera(2, cv=cv), good)
        bad.release.assert_called_once()
        good.release.assert_not_called()
        self.assertEqual([c.args for c in cv.VideoCapture.call_args_list], [(2, 700), (2, 1400)])

    def test_cancelled_camera_probe_does_not_open_device(self):
        stop = threading.Event()
        stop.set()
        cv = Mock()
        with self.assertRaises(RuntimeError):
            pc_runtime.open_camera(stop_event=stop, cv=cv)
        cv.VideoCapture.assert_not_called()

    def test_data_and_bundle_paths_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"ANTI_FINGER_DATA_DIR": folder}):
                with patch.object(sys, "_MEIPASS", "C:/bundle", create=True):
                    self.assertEqual(Path(pc_runtime.data_path("report_state.json")), Path(folder) / "report_state.json")
                    self.assertEqual(Path(pc_runtime.resource_path("Voices", "006.mp3")), Path("C:/bundle/Voices/006.mp3"))

    def test_task_contains_landmark_model(self):
        factory = Mock()
        pc_runtime.load_landmark_model(factory, 2)
        self.assertGreater(len(factory.call_args.kwargs["model_content"]), 100000)
        self.assertEqual(factory.call_args.kwargs["num_threads"], 2)
        factory.return_value.allocate_tensors.assert_called_once()


if __name__ == "__main__":
    unittest.main()
