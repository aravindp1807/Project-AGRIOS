import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import sys
import os

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.open_meteo import fetch_open_meteo

class TestOpenMeteo(unittest.TestCase):
    
    @patch('ingestion.open_meteo.requests.get')
    def test_fetch_open_meteo_success(self, mock_get):
        # Mock Open-Meteo API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "latitude": 40.0,
            "longitude": -100.0,
            "timezone": "UTC",
            "daily": {
                "time": ["2026-06-01", "2026-06-02"],
                "temperature_2m_max": [25.5, 27.0],
                "precipitation_sum": [0.0, 1.5]
            }
        }
        mock_get.return_value = mock_response
        
        aoi = {
            "id": "test-aoi",
            "latitude": 40.0,
            "longitude": -100.0
        }
        
        results = fetch_open_meteo(aoi)
        
        # We expect 4 results:
        # - Temperature: 2026-06-01 (25.5), 2026-06-02 (27.0)
        # - Precipitation: 2026-06-01 (0.0), 2026-06-02 (1.5)
        self.assertEqual(len(results), 4)
        
        temp_reading = next(r for r in results if r.metric_type == "temperature" and r.reading_date == date(2026, 6, 1))
        self.assertEqual(temp_reading.value, 25.5)
        self.assertEqual(temp_reading.unit, "C")
        self.assertEqual(temp_reading.source, "open_meteo")
        
        precip_reading = next(r for r in results if r.metric_type == "precipitation" and r.reading_date == date(2026, 6, 2))
        self.assertEqual(precip_reading.value, 1.5)
        self.assertEqual(precip_reading.unit, "mm")

if __name__ == '__main__':
    unittest.main()
