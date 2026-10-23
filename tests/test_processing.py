"""Pruebas sintéticas del procesamiento; no requieren antena ni GUI."""
import unittest
from starlink_monitor_v2 import SessionData, KEYS, percentile

class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.session = SessionData()

    def batch(self, end, loss):
        n = len(loss)
        return self.session.ingest(
            {'end_counter': end, 'samples': n},
            {KEYS[0]: [30.0]*n, KEYS[1]: loss,
             KEYS[2]: [8e6]*n, KEYS[3]: [0.0]*n, 'power_w': [36.0]*n},
            1700000000)

    def test_duplicates_and_contiguous_loss(self):
        self.batch(103, [0, 1, 1])
        rows, _ = self.batch(103, [0, 1, 1])
        self.assertEqual(rows, [])
        self.batch(105, [1, 0])
        self.assertEqual(self.session.n, 5)
        self.assertEqual(self.session.runs, 1)
        self.assertEqual(self.session.max_run, 3)
        self.assertEqual(len(self.session.latencies), 2)

    def test_gap_and_reset_break_runs(self):
        self.batch(103, [1, 1])
        self.batch(110, [1, 1])
        self.assertEqual(self.session.missing, 5)
        self.batch(2, [1, 0])
        self.assertEqual(self.session.resets, 1)
        self.assertEqual(self.session.runs, 3)
        self.assertEqual(self.session.max_run, 2)

    def test_energy_and_traffic(self):
        self.batch(3, [0, 0, 0])
        summary = self.session.summary()
        self.assertEqual(summary['descarga_MB_observados'], 3)
        self.assertAlmostEqual(summary['energia_Wh_observada'], .03)

    def test_missing_values_remain_unknown(self):
        rows, _ = self.session.ingest({'end_counter': 1, 'samples': 1}, {}, 1700000000)
        self.assertIsNone(rows[0]['power_w'])
        self.assertIsNone(self.session.summary()['energia_Wh_observada'])
        self.assertIsNone(self.session.summary()['perdida_media_pct'])

    def test_p95_interpolation(self):
        self.assertAlmostEqual(percentile([10, 20, 30, 40, 50], .95), 48)
        self.assertIsNone(percentile([], .95))

if __name__ == '__main__':
    unittest.main()
