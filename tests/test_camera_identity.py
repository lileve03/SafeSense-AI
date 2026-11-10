import unittest
from unittest.mock import patch
from backend import registry
class CameraIdentityTests(unittest.TestCase):
 def test_registry_only_and_ambiguous_fail_closed(self):
  rows=[{'camera_id':'CAM_HALL','camera_name':'School Hall','aliases':['hall replay']},{'camera_id':'CAM_ENTRANCE','camera_name':'School Entrance'}]
  with patch.object(registry,'cameras',return_value=rows):
   for value in [' cam-hall ','School Hall','hall replay']:self.assertEqual(registry.canonical_camera_id(value),'CAM_HALL')
   for value in [None,'UNKNOWN','ZONE_SCHOOL_HALL','adl_02']:self.assertIsNone(registry.canonical_camera_id(value))
  with patch.object(registry,'cameras',return_value=[{'camera_id':'A','aliases':['shared']},{'camera_id':'B','aliases':['shared']}]):self.assertIsNone(registry.canonical_camera_id('shared'))
if __name__=='__main__':unittest.main()
