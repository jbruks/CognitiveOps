"""Offline L4/L3 geo lab POC unit checks (no API or hardware)."""
import unittest
from mf_dod_map_recon_poc import parse_response,pixel_to_wgs84

class GeoReconTests(unittest.TestCase):
    def test_strict_json(self):
        self.assertEqual(parse_response('{"a":1}',("a",)),{"a":1})
        with self.assertRaises(ValueError):
            parse_response('{"a":1,"b":2}',("a",))
    def test_out_of_bounds(self):
        class Map:
            crs="EPSG:4326"
            width=100
            height=100
        with self.assertRaises(ValueError):
            pixel_to_wgs84(Map(),-1,50)
        with self.assertRaises(ValueError):
            pixel_to_wgs84(Map(),100,50)
    def test_pixel_to_gps(self):
        try:
            from affine import Affine
        except ImportError:
            self.skipTest("rasterio dependency not installed")
        class Map:
            crs="EPSG:4326"
            width=100
            height=100
            transform=Affine.translation(-1,40)*Affine.scale(.01,-.01)
        lat,lon=pixel_to_wgs84(Map(),0,0)
        self.assertAlmostEqual(lat,39.995,5)
        self.assertAlmostEqual(lon,-.995,5)

if __name__=="__main__":
    unittest.main()
