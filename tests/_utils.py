import datetime
import unittest

import rule_engine._utils as utils
import rule_engine.errors as errors

class UtilityTests(unittest.TestCase):
    def test_parse_timedelta(self):
        self.assertEqual(utils.parse_timedelta('PT'), datetime.timedelta())
        self.assertEqual(utils.parse_timedelta('P1W'), datetime.timedelta(weeks=1))
        self.assertEqual(utils.parse_timedelta('P1D'), datetime.timedelta(days=1))
        self.assertEqual(utils.parse_timedelta('PT1H'), datetime.timedelta(hours=1))
        self.assertEqual(utils.parse_timedelta('PT1M'), datetime.timedelta(minutes=1))
        self.assertEqual(utils.parse_timedelta('PT1S'), datetime.timedelta(seconds=1))


    def test_parse_timedelta_error(self):
        with self.assertRaisesRegex(errors.TimedeltaSyntaxError, 'empty timedelta string'):
            utils.parse_timedelta('P')
        with self.assertRaisesRegex(errors.TimedeltaSyntaxError, 'invalid timedelta string'):
            utils.parse_timedelta('1W')
        with self.assertRaisesRegex(errors.TimedeltaSyntaxError, 'invalid timedelta string'):
            utils.parse_timedelta('p1w')
        with self.assertRaisesRegex(errors.TimedeltaSyntaxError, 'invalid timedelta string'):
            utils.parse_timedelta('PZ')
