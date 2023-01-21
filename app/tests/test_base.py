from django.test import TestCase

import app.tasks as tasks

class TestTest(TestCase):
    def test_test(self):
        """
        Test that it can sum a list of integers
        """
        data = [1, 2, 3]
        result = sum(data)
        self.assertEqual(result, 6)

class Test_get_special_status_predict(TestCase):

    def test_get_special_status_predict_instances(self):
        outdoorNow = 0
        next_hour_airtemperature = 0
        special_status_status, special_mode, zone1delta, zone2delta = tasks.get_special_status_predict(outdoorNow, next_hour_airtemperature)
        self.assertIsInstance(special_status_status, list)
        self.assertIsInstance(special_status_status[0], dict)
        self.assertIsInstance(special_mode, int)
        self.assertIsInstance(zone1delta, int)
        self.assertIsInstance(zone2delta, int)

    def test_get_special_status_predict_comfort(self):
        outdoorNow = 0
        for next_hour_airtemperature in range(5, 30):
            special_status_status, special_mode, zone1delta, zone2delta = tasks.get_special_status_predict(outdoorNow, next_hour_airtemperature)
            self.assertIsInstance(special_status_status, list)
            self.assertIsInstance(special_status_status[0], dict)
            self.assertIsInstance(special_mode, int)
            self.assertIsInstance(zone1delta, int)
            self.assertIsInstance(zone2delta, int)
            self.assertEqual(special_mode, 1, msg=f'{outdoorNow}->{next_hour_airtemperature} {special_mode}')

    def test_get_special_status_predict_comfort_false(self):
        outdoorNow = 0
        for next_hour_airtemperature in range(-4, 5):
            special_status_status, special_mode, zone1delta, zone2delta = tasks.get_special_status_predict(outdoorNow, next_hour_airtemperature)
            self.assertIsInstance(special_status_status, list)
            self.assertIsInstance(special_status_status[0], dict)
            self.assertIsInstance(special_mode, int)
            self.assertIsInstance(zone1delta, int)
            self.assertIsInstance(zone2delta, int)
            self.assertEqual(special_mode, 0, msg=f'{outdoorNow}->{next_hour_airtemperature} {special_mode}')

    def test_get_special_status_predict_eco(self):
        outdoorNow = 5
        for next_hour_airtemperature in range(0, -25, -1):
            special_status_status, special_mode, zone1delta, zone2delta = tasks.get_special_status_predict(outdoorNow, next_hour_airtemperature)
            self.assertIsInstance(special_status_status, list)
            self.assertIsInstance(special_status_status[0], dict)
            self.assertIsInstance(special_mode, int)
            self.assertIsInstance(zone1delta, int)
            self.assertIsInstance(zone2delta, int)
            self.assertEqual(special_mode, 2, msg=f'{outdoorNow}->{next_hour_airtemperature} {special_mode}')

    def test_get_special_status_predict_eco_false(self):
        outdoorNow = 4
        for next_hour_airtemperature in range(0, -25, -1):
            special_status_status, special_mode, zone1delta, zone2delta = tasks.get_special_status_predict(outdoorNow, next_hour_airtemperature)
            self.assertIsInstance(special_status_status, list)
            self.assertIsInstance(special_status_status[0], dict)
            self.assertIsInstance(special_mode, int)
            self.assertIsInstance(zone1delta, int)
            self.assertIsInstance(zone2delta, int)
            self.assertEqual(special_mode, 0, msg=f'{outdoorNow}->{next_hour_airtemperature} {special_mode}')