import unittest

from bench.paths import matches, any_match


class TestMatches(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(matches("out/banner.txt", "out/banner.txt"))
        self.assertFalse(matches("out/banner2.txt", "out/banner.txt"))

    def test_directory_prefix_self(self):
        self.assertTrue(matches("out", "out/"))
        self.assertTrue(matches("out/banner.txt", "out/"))
        self.assertTrue(matches("out/nested/deep.txt", "out/"))

    def test_directory_prefix_non_match(self):
        self.assertFalse(matches("output.txt", "out/"))
        self.assertFalse(matches("other/banner.txt", "out/"))

    def test_single_segment_glob(self):
        self.assertTrue(matches("out/x.json", "out/*.json"))
        self.assertFalse(matches("out/sub/x.json", "out/*.json"))  # * does not cross /
        self.assertFalse(matches("out/x.txt", "out/*.json"))

    def test_question_mark_glob(self):
        self.assertTrue(matches("out/a.txt", "out/?.txt"))
        self.assertFalse(matches("out/ab.txt", "out/?.txt"))

    def test_any_match_true_on_any(self):
        self.assertTrue(any_match("out/x.json", ["other/", "out/*.json"]))

    def test_any_match_false_on_none(self):
        self.assertFalse(any_match("out/x.json", ["other/", "out/*.txt"]))

    def test_any_match_empty_patterns(self):
        self.assertFalse(any_match("anything", []))


if __name__ == "__main__":
    unittest.main()
