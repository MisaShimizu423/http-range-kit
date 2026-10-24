import unittest

from http_range_kit.core import (
    parse_range,
    parse_content_range,
    RangeSpec,
    ContentRange,
)


class TestParseRange(unittest.TestCase):
    def test_simple_range(self):
        result = parse_range("bytes=0-499", 1000)
        self.assertEqual(result, RangeSpec("bytes", 0, 499, 500, 1000))

    def test_range_from_middle(self):
        result = parse_range("bytes=500-999", 1000)
        self.assertEqual(result, RangeSpec("bytes", 500, 999, 500, 1000))

    def test_open_ended_range(self):
        result = parse_range("bytes=950-", 1000)
        self.assertEqual(result, RangeSpec("bytes", 950, 999, 50, 1000))

    def test_suffix_range(self):
        result = parse_range("bytes=-500", 1000)
        self.assertEqual(result, RangeSpec("bytes", 500, 999, 500, 1000))

    def test_suffix_range_larger_than_total(self):
        # If the suffix is larger than the total, return the whole resource.
        result = parse_range("bytes=-1500", 1000)
        self.assertEqual(result, RangeSpec("bytes", 0, 999, 1000, 1000))

    def test_range_end_exceeds_total(self):
        # The end position should be clamped to the last byte.
        result = parse_range("bytes=950-2000", 1000)
        self.assertEqual(result, RangeSpec("bytes", 950, 999, 50, 1000))

    def test_range_single_byte(self):
        result = parse_range("bytes=999-999", 1000)
        self.assertEqual(result, RangeSpec("bytes", 999, 999, 1, 1000))

    def test_multi_range_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=0-50,100-150", 1000)

    def test_non_bytes_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_range("items=0-499", 1000)

    def test_malformed_header_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=0-499-extra", 1000)

    def test_open_ended_beyond_total_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=1000-", 1000)

    def test_unsatisfiable_range_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=500-", 0)

    def test_suffix_zero_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=-0", 1000)

    def test_negative_start_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=-1-499", 1000)

    def test_end_less_than_start_raises(self):
        with self.assertRaises(ValueError):
            parse_range("bytes=500-400", 1000)


class TestParseContentRange(unittest.TestCase):
    def test_simple_content_range(self):
        result = parse_content_range("bytes 0-499/1000")
        self.assertEqual(result, ContentRange("bytes", 0, 499, 1000))

    def test_unknown_total_content_range(self):
        result = parse_content_range("bytes 0-499/*")
        self.assertEqual(result, ContentRange("bytes", 0, 499, None))

    def test_single_byte_content_range(self):
        result = parse_content_range("bytes 999-999/1000")
        self.assertEqual(result, ContentRange("bytes", 999, 999, 1000))

    def test_non_bytes_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_content_range("items 0-499/1000")

    def test_malformed_content_range_raises(self):
        with self.assertRaises(ValueError):
            parse_content_range("bytes 0-499")

    def test_unsatisfiable_content_range_raises(self):
        with self.assertRaises(ValueError):
            parse_content_range("bytes */1000")

    def test_negative_total_raises(self):
        with self.assertRaises(ValueError):
            parse_content_range("bytes 0-499/-1")

    def test_end_less_than_start_raises(self):
        with self.assertRaises(ValueError):
            parse_content_range("bytes 500-400/1000")


if __name__ == "__main__":
    unittest.main()
