import unittest
from unittest.mock import patch
from private_sensor_simulator import send_test_event

class TestPrivateSensorSimulator(unittest.TestCase):
    @patch('private_sensor_simulator.api_request')
    def test_fall_uses_simulation_source(self, api):
        send_test_event('http://127.0.0.1:8000', 'Demo-Private-A', 'fall')
        self.assertEqual(api.call_args.args[2]['source'], 'simulation')
        self.assertEqual(api.call_args.args[2]['type'], 'fall')

    @patch('private_sensor_simulator.api_request')
    def test_sos_uses_simulation_source(self, api):
        send_test_event('http://127.0.0.1:8000', 'Demo-Private-A', 'sos')
        self.assertEqual(api.call_args.args[2]['source'], 'simulation')

    def test_reject_invalid_event(self):
        with self.assertRaises(ValueError):
            send_test_event('http://127.0.0.1:8000', 'Demo-Private-A', 'vision')

    def test_reject_invalid_confidence(self):
        with self.assertRaises(ValueError):
            send_test_event('http://127.0.0.1:8000', 'Demo-Private-A', 'fall', 2)

if __name__ == '__main__':
    unittest.main()
