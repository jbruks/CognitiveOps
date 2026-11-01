import unittest
from mf_dod_shadow_sonar import ReadOnlySonar, parse_distance


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.writes = []
        self.lines = [b"DISTANCE_CM=-1.0 BLOCKED=0 SENSOR_STATE=CLEAR\n",
                      b"DISTANCE_CM=75.0 BLOCKED=0 SENSOR_STATE=CLEAR\n"]
        self.closed = False

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def close(self):
        self.closed = True


class SonarShadowTests(unittest.TestCase):
    def test_no_echo_is_invalid_not_clear(self):
        sample = parse_distance("DISTANCE_CM=-1.0 BLOCKED=0 SENSOR_STATE=CLEAR")
        self.assertFalse(sample["front_distance_valid"])
        self.assertIsNone(sample["front_blocked"])

    def test_valid_blocked(self):
        sample = parse_distance("DISTANCE_CM=18.0 BLOCKED=1 SENSOR_STATE=BLOCKED")
        self.assertTrue(sample["front_distance_valid"])
        self.assertTrue(sample["front_blocked"])

    def test_malformed_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_distance("ACK ARM")

    def test_only_get_distance_command(self):
        port = FakeSerial()
        sonar = ReadOnlySonar(serial_factory=lambda *a, **kw: port).open()
        self.assertFalse(sonar.read()["front_distance_valid"])
        self.assertTrue(sonar.read()["front_distance_valid"])
        self.assertEqual(port.writes, [b"GET_DISTANCE\n", b"GET_DISTANCE\n"])
        sonar.close()
        self.assertTrue(port.closed)

    def test_no_actuator_interface(self):
        sonar = ReadOnlySonar(serial_factory=FakeSerial)
        for name in ("arm", "connect_and_prepare", "stop",
                     "execute_tactical_action", "disarm"):
            self.assertFalse(hasattr(sonar, name))


if __name__ == "__main__":
    unittest.main()
