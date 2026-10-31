"""Self-tests for the OKTI encoder and decoder."""

import sys
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from okti_codec import OktiError, decode_okti, encode_pixels, read_ppm, write_ppm

DATA = Path(__file__).parent / "data"


class OktiCodecTests(unittest.TestCase):
    def test_tiny_official_example(self):
        width, height, pixels = read_ppm(DATA / "tiny.ppm")
        self.assertEqual((width, height), (2, 2))
        self.assertEqual(encode_pixels(width, height, pixels),
                         "okti\n2 2\npff0000\npffffff\np00ff00\np0000ff\n")

    def test_sample_images_round_trip_and_pixel_modes(self):
        cases = {
            "pixels_small.ppm": "p",
            "differences_small.ppm": "d",
            "runs_short_small.ppm": "r",
            "runs_long_small.ppm": "R",
            "smallindices_small.ppm": "i",
            "runs_and_short_indices_small.ppm": "ir",
        }
        for filename, expected_modes in cases.items():
            with self.subTest(filename=filename):
                width, height, pixels = read_ppm(DATA / filename)
                encoded = encode_pixels(width, height, pixels)
                decoded = decode_okti(encoded)
                self.assertEqual(decoded, (width, height, pixels))
                self.assertTrue(any(mode in line for mode in expected_modes for line in encoded.splitlines()[2:]))

    def test_all_token_types_and_initial_black(self):
        sample = "okti\n8 1\nd88a\npff0000\nr1\nR01\ni0\nI00\np00ff00\nd88f\n"
        width, height, pixels = decode_okti(sample)
        self.assertEqual((width, height), (8, 1))
        self.assertEqual(pixels[0], (0, 0, 2))
        self.assertEqual(pixels[2:5], [(255, 0, 0)] * 3)

    def test_invalid_header_dimensions_and_pixel_type(self):
        for text in ("nope\n1 1\np000000\n", "okti\n0 1\n", "okti\n1 1\nx000000\n"):
            with self.subTest(text=text), self.assertRaises(OktiError):
                decode_okti(text)
        with self.assertRaises(OktiError) as error:
            decode_okti("okti\n1 1\n?\n")
        self.assertIn("line 3", str(error.exception))
        self.assertIn("'?'", str(error.exception))

    def test_run_can_span_rows_and_be_split_at_255(self):
        pixels = [(7, 8, 9)] * 600
        encoded = encode_pixels(3, 200, pixels)
        self.assertIn("Rff", encoded)
        self.assertEqual(decode_okti(encoded), (3, 200, pixels))

    def test_ppm_read_write_round_trip_and_binary_whitespace(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "roundtrip.ppm"
            source_pixels = [(10, 32, 13), (255, 0, 255)]
            write_ppm(output, 2, 1, source_pixels)
            self.assertEqual(read_ppm(output), (2, 1, source_pixels))
            ascii_ppm = Path(directory) / "ascii.ppm"
            ascii_ppm.write_text("P3\n# test comment\n1 1\n255\n1 2 3\n", encoding="ascii")
            self.assertEqual(read_ppm(ascii_ppm), (1, 1, [(1, 2, 3)]))

    def test_tokens_without_line_breaks(self):
        self.assertEqual(decode_okti("okti\n2 1\np000000p010203"),
                         (2, 1, [(0, 0, 0), (1, 2, 3)]))


if __name__ == "__main__":
    unittest.main()
