"""Regression: legacy camera must validate backend zone permission before loading/capturing."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock, MagicMock
from ai_models.vision import yolo_pose_camera, yolo_pose_temporal
from ai_models.acoustic import yamnet_microphone
import json

class PrivacyAdapters(unittest.TestCase):
    def test_private_camera_never_opens(self):
        with patch.object(yolo_pose_camera,'args_parser',return_value=SimpleNamespace(zone='ZONE_TOILET_BLINDSPOT',api='http://local')):
            with patch.object(yolo_pose_camera,'authorize_zone',side_effect=RuntimeError('private')):
                with patch.object(yolo_pose_camera.cv2,'VideoCapture') as camera, patch.object(yolo_pose_camera,'YOLO') as model:
                    with self.assertRaises(SystemExit): yolo_pose_camera.main()
                    camera.assert_not_called();model.assert_not_called()

    def test_backend_unavailable_camera_never_opens(self):
        with patch.object(yolo_pose_camera,'args_parser',return_value=SimpleNamespace(zone='ZONE_CORRIDOR_A',api='http://local')):
            with patch.object(yolo_pose_camera,'authorize_zone',side_effect=OSError('offline')):
                with patch.object(yolo_pose_camera.cv2,'VideoCapture') as camera:
                    with self.assertRaises(SystemExit):yolo_pose_camera.main()
                    camera.assert_not_called()

    def test_private_zone_cannot_be_authorized(self):
        response=Mock();response.json.return_value=[{'id':'ZONE_TOILET_BLINDSPOT','name':'Toilet','zone_type':'PRIVATE','allowed_sources':['radar']}]
        with patch.object(yolo_pose_temporal.requests,'get',return_value=response):
            with self.assertRaises(RuntimeError):yolo_pose_temporal.authorize_zone('http://local','ZONE_TOILET_BLINDSPOT')

    def test_speech_has_no_acoustic_event_mapping(self):
        self.assertEqual(yamnet_microphone.choose_classes(['Speech','Conversation','Narration']) , {'scream':[],'impact':[]})

    def test_yamnet_posts_model_provenance_without_audio(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"status":"ok"}'
        with patch.object(yamnet_microphone.request,'urlopen',return_value=response) as send:
            yamnet_microphone.post_event('http://local','ZONE_TOILET_BLINDSPOT','scream',.8)
        payload=json.loads(send.call_args.args[0].data)
        self.assertEqual(payload['processing_mode'],'real_model')
        self.assertEqual(payload['score'],.8)
        self.assertFalse({'audio','waveform','transcript'}.intersection(payload))

if __name__=='__main__':unittest.main()
