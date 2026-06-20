import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import sqlite3

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.llm_router import LLMRouter, SynthesisResult
from analysis.alerting import evaluate_metric_alerts, check_and_create_alerts
from processing.trends import TrendResult

class TestLLMRouterAndAlerting(unittest.TestCase):
    
    def test_local_rule_based_fallback(self):
        router = LLMRouter()
        # Set all keys to empty to force fallback
        router.openrouter_key = ""
        router.gemini_key = ""
        router.groq_key = ""
        router.nvidia_key = ""
        
        context = {
            "aoi_name": "Kansas Farm",
            "metrics": [
                {
                    "name": "temperature",
                    "value": 35.0,
                    "unit": "C",
                    "baseline": 25.0,
                    "deviation_pct": 40.0,
                    "direction": "rising"
                },
                {
                    "name": "precipitation",
                    "value": 1.0,
                    "unit": "mm",
                    "baseline": 2.0,
                    "deviation_pct": -50.0,
                    "direction": "falling"
                }
            ]
        }
        
        result = router.synthesize("Some prompt", "search", fallback_context_data=context)
        self.assertEqual(result.provider_used, "local_rule_engine")
        self.assertIn("Kansas Farm", result.text)
        self.assertIn("CRITICAL DEVIATION DETECTED", result.text)
        self.assertIn("temperature", result.text.lower())
        self.assertIn("precipitation", result.text.lower())

    def test_evaluate_metric_alerts(self):
        # 1. Critical deviation (>30%)
        trend = TrendResult(slope=0.5, direction="rising", deviation_pct=35.0)
        alert = evaluate_metric_alerts("aoi-1", "temperature", trend, baseline=20.0, recent_readings=[15, 17, 27])
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "critical")
        
        # 2. Warning deviation (15%-30%)
        trend = TrendResult(slope=0.1, direction="rising", deviation_pct=20.0)
        alert = evaluate_metric_alerts("aoi-1", "temperature", trend, baseline=20.0, recent_readings=[18, 19, 24])
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "warning")
        
        # 3. Stable / under threshold (<15%)
        trend = TrendResult(slope=0.01, direction="stable", deviation_pct=5.0)
        alert = evaluate_metric_alerts("aoi-1", "temperature", trend, baseline=20.0, recent_readings=[19, 20, 21])
        self.assertIsNone(alert)

        # 4. 3+ consecutive readings beyond warning (15%) trending same direction
        # Baseline = 20. Warning boundary = 20 * 1.15 = 23 (above) or 20 * 0.85 = 17 (below)
        # Recent readings: 24, 25, 26 (all above 23, and strictly rising)
        trend = TrendResult(slope=1.0, direction="rising", deviation_pct=25.0)
        alert = evaluate_metric_alerts("aoi-1", "temperature", trend, baseline=20.0, recent_readings=[24, 25, 26])
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "critical")
        self.assertIn("consecutive readings", alert["message"])

if __name__ == '__main__':
    unittest.main()
