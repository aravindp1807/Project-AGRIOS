import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import sys
import os

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.nasa_power import fetch_nasa_power
from ingestion.base import IngestionResult

class TestNasaPower(unittest.TestCase):
    
    @patch('ingestion.nasa_power.requests.get')
    def test_fetch_nasa_power_success(self, mock_get):
        # Mock NASA POWER API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {
                        "20231001": 15.5,
                        "20231002": -999.0  # Should be skipped
                    },
                    "PRECTOTCORR": {
                        "20231001": 0.0,
                        "20231002": 1.2
                    },
                    "ALLSKY_SFC_SW_DWN": {
                        "20231001": 12.5,
                        "20231002": 10.0
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Test input AOI
        aoi = {
            "id": "test-aoi",
            "latitude": 40.0,
            "longitude": -100.0
        }
        
        results = fetch_nasa_power(aoi)
        
        # We expect 5 results:
        # - T2M: 2023-10-01 (15.5) -> 1
        # - PRECTOTCORR: 2023-10-01 (0.0), 2023-10-02 (1.2) -> 2
        # - ALLSKY_SFC_SW_DWN: 2023-10-01 (12.5), 2023-10-02 (10.0) -> 2
        # T2M 2023-10-02 has -999.0 and should be skipped
        self.assertEqual(len(results), 5)
        
        # Verify specific items
        t2m_reading = next(r for r in results if r.metric_type == "temperature" and r.reading_date == date(2023, 10, 1))
        self.assertEqual(t2m_reading.value, 15.5)
        self.assertEqual(t2m_reading.unit, "C")
        self.assertEqual(t2m_reading.source, "nasa_power")
        self.assertEqual(t2m_reading.area_id, "test-aoi")
        
        precip_reading = next(r for r in results if r.metric_type == "precipitation" and r.reading_date == date(2023, 10, 2))
        self.assertEqual(precip_reading.value, 1.2)
        
        # Check that -999.0 was indeed skipped
        t2m_skipped = [r for r in results if r.metric_type == "temperature" and r.reading_date == date(2023, 10, 2)]
        self.assertEqual(len(t2m_skipped), 0)

if __name__ == '__main__':
    unittest.main()
