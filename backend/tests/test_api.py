import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os
import sys
import tempfile
import sqlite3

# Adjust path to find backend files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment database
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()

os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

from main import app
from db.connection import get_db

class TestAPI(unittest.TestCase):
    
    def setUp(self):
        # Always run database initialization before tests
        from db.connection import init_db
        init_db()
        self.client = TestClient(app)
        
    def tearDown(self):
        # Remove the temp database after tests
        try:
            os.unlink(temp_db_path)
        except OSError:
            pass

    def test_aoi_crud_endpoints(self):
        # 1. Create AOI
        payload = {
            "name": "Test Farm",
            "latitude": 38.5,
            "longitude": -98.2,
            "radius_km": 15.0,
            "is_watched": True
        }
        res = self.client.post("/aoi", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Test Farm")
        self.assertEqual(data["is_watched"], True)
        
        aoi_id = data["id"]
        
        # 2. Get AOI
        res = self.client.get(f"/aoi/{aoi_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Test Farm")
        
        # 3. List AOIs
        res = self.client.get("/aoi")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        
        # 4. Update AOI
        res = self.client.patch(f"/aoi/{aoi_id}", json={"name": "Updated Test Farm", "is_watched": False})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Updated Test Farm")
        self.assertEqual(res.json()["is_watched"], False)
        
        # 5. Delete AOI
        res = self.client.delete(f"/aoi/{aoi_id}")
        self.assertEqual(res.status_code, 204)
        
        # 6. Verify Delete
        res = self.client.get(f"/aoi/{aoi_id}")
        self.assertEqual(res.status_code, 404)

    @patch('ingestion.nasa_power.requests.get')
    def test_search_endpoint_flow(self, mock_get):
        # Mock NASA POWER API response with a single temperature record
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {
                        "20260601": 24.5,
                        "20260602": 25.5
                    },
                    "PRECTOTCORR": {
                        "20260601": 0.0,
                        "20260602": 0.5
                    },
                    "ALLSKY_SFC_SW_DWN": {
                        "20260601": 18.0,
                        "20260602": 19.5
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Create an AOI first
        payload = {
            "name": "Search Test Farm",
            "latitude": 35.0,
            "longitude": -90.0,
            "radius_km": 10.0,
            "is_watched": False
        }
        create_res = self.client.post("/aoi", json=payload)
        aoi_id = create_res.json()["id"]

        # Call POST /search
        search_payload = {
            "area_id": aoi_id,
            "modes": ["weather"]
        }
        
        search_res = self.client.post("/search", json=search_payload)
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.json()
        
        # Verify response attributes
        self.assertEqual(search_data["area_id"], aoi_id)
        self.assertIn("report_text", search_data)
        self.assertIn("provider_used", search_data)
        self.assertTrue(len(search_data["readings"]) > 0)
        
        # Verify baselines got calculated and saved
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM baselines WHERE area_id = ?", (aoi_id,))
            baselines_count = cursor.fetchone()["count"]
            self.assertTrue(baselines_count > 0)
            
            # Verify report got cached
            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE area_id = ?", (aoi_id,))
            reports_count = cursor.fetchone()["count"]
            self.assertEqual(reports_count, 1)

    def test_map_overlay_endpoint(self):
        res = self.client.get("/map/gibs-tile-url?layer=MODIS_Terra_NDVI_8Day&date=2023-10-24")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("url_template", data)
        self.assertIn("MODIS_Terra_NDVI_8Day", data["url_template"])
        self.assertIn("2023-10-24", data["url_template"])

if __name__ == '__main__':
    unittest.main()
