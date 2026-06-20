import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import sys
import os

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.usgs_water import fetch_usgs_water

class TestUsgsWater(unittest.TestCase):
    
    @patch('ingestion.usgs_water.requests.get')
    def test_fetch_usgs_water_success(self, mock_get):
        # Mock USGS IV response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": {
                "timeSeries": [
                    {
                        "sourceInfo": {
                            "siteName": "CLOSEST CREEK AT CO",
                            "siteCode": [{"value": "111111"}],
                            "geoLocation": {
                                "geogLocation": {
                                    "latitude": 39.1,
                                    "longitude": -105.1
                                }
                            }
                        },
                        "variable": {
                            "variableCode": [{"value": "00060"}],
                            "variableName": "Discharge",
                            "unit": {"unitCode": "cfs"}
                        },
                        "values": [
                            {
                                "value": [
                                    {"value": "100", "dateTime": "2026-06-01T12:00:00.000-06:00"},
                                    {"value": "120", "dateTime": "2026-06-01T18:00:00.000-06:00"}
                                ]
                            }
                        ]
                    },
                    {
                        "sourceInfo": {
                            "siteName": "FARWAY RIVER AT CO",
                            "siteCode": [{"value": "222222"}],
                            "geoLocation": {
                                "geogLocation": {
                                    "latitude": 45.0,
                                    "longitude": -115.0
                                }
                            }
                        },
                        "variable": {
                            "variableCode": [{"value": "00060"}],
                            "variableName": "Discharge",
                            "unit": {"unitCode": "cfs"}
                        },
                        "values": [
                            {
                                "value": [
                                    {"value": "500", "dateTime": "2026-06-01T12:00:00.000-06:00"}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        aoi = {
            "id": "test-aoi",
            "latitude": 39.0,
            "longitude": -105.0,
            "radius_km": 20.0
        }
        
        results = fetch_usgs_water(aoi)
        
        # We expect only the closest site ("111111") to be processed.
        # It has 2 readings on 2026-06-01 (100 and 120), so the daily average should be 110.0 cfs.
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r.source, "usgs_water")
        self.assertEqual(r.metric_type, "water_discharge")
        self.assertEqual(r.value, 110.0)
        self.assertEqual(r.unit, "cfs")
        self.assertEqual(r.reading_date, date(2026, 6, 1))

if __name__ == '__main__':
    unittest.main()
