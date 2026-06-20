import unittest
from datetime import date, timedelta
import sys
import os

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.baselines import compute_baseline
from processing.trends import detect_trend, calculate_linear_regression

class TestTrendsAndBaselines(unittest.TestCase):
    
    def test_compute_baseline(self):
        # Normal average
        self.assertEqual(compute_baseline([10.0, 20.0, 30.0]), 20.0)
        # Empty list should return None
        self.assertIsNone(compute_baseline([]))
        
    def test_calculate_linear_regression(self):
        # Perfect positive line: y = 2x + 5
        x = [0.0, 1.0, 2.0, 3.0]
        y = [5.0, 7.0, 9.0, 11.0]
        self.assertAlmostEqual(calculate_linear_regression(x, y), 2.0)
        
        # Single element or empty should return 0.0
        self.assertEqual(calculate_linear_regression([1.0], [5.0]), 0.0)
        self.assertEqual(calculate_linear_regression([], []), 0.0)

    def test_detect_trend_rising(self):
        # 5 days of rising values
        start_date = date(2023, 10, 1)
        readings = [
            (start_date, 10.0),
            (start_date + timedelta(days=1), 12.0),
            (start_date + timedelta(days=2), 14.0),
            (start_date + timedelta(days=3), 16.0),
            (start_date + timedelta(days=4), 18.0)
        ]
        
        # Mean = 14.0. Slope = 2.0. Threshold = 0.02 * 14 = 0.28
        # Since slope (2.0) > 0.28, it should be rising.
        # Latest val = 18.0. Baseline = 10.0. Deviation = ((18 - 10) / 10) * 100 = 80%
        result = detect_trend(readings, baseline=10.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.direction, "rising")
        self.assertAlmostEqual(result.slope, 2.0)
        self.assertAlmostEqual(result.deviation_pct, 80.0)

    def test_detect_trend_stable(self):
        # Values fluctuate very slightly
        start_date = date(2023, 10, 1)
        readings = [
            (start_date, 100.0),
            (start_date + timedelta(days=1), 100.5),
            (start_date + timedelta(days=2), 99.8),
            (start_date + timedelta(days=3), 100.2)
        ]
        
        # Mean is around 100.1. Threshold is 0.02 * 100 = 2.0
        # Slope will be very close to 0, which is < 2.0, so stable.
        result = detect_trend(readings, baseline=100.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.direction, "stable")

if __name__ == '__main__':
    unittest.main()
