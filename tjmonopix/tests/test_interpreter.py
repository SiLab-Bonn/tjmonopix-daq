import unittest
import numpy as np
from tjmonopix.analysis import interpreter


class TestInterpreter(unittest.TestCase):
    def setUp(self):
        hit_dtype = [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"),
                     ("timestamp", "<i8")]

        # Test data contains five TJ data blocks, one TDC data, one TLU data, one TLU timestamp
        self.correct_raw_data = np.array([119565277, 533409971, 654311425, 805306368, 117615582, 533409971,
                                          654311425, 805306368, 111038963, 533410220, 671088641, 805306368,
                                          110957044, 533410220, 671088641, 805306368, 98674900, 533410806, 687865857,
                                          805306368, 1661002752, 1644167572, 1633608547, 3258017254, 1929379840,
                                          1912686510, 1902803753])

        # Test data is missing one TJ and one TLU timestamp data word
        self.broken_raw_data = np.array([119565277, 654311425, 805306368, 117615582, 533409971,
                                        654311425, 805306368, 111038963, 533410220, 671088641, 805306368,
                                        110957044, 533410220, 671088641, 805306368, 98674900, 533410806, 687865857,
                                        805306368, 1661002752, 1644167572, 1633608547, 3258017254, 1929379840])

        self.expected_correct_hit_data = np.array([(59, 175, 57, 0, 0, 8534559536),
                                                   (60, 175, 56, 5, 0, 8534559536),
                                                   (103, 71, 52, 60, 0, 8534563520),
                                                   (104, 71, 52, 58, 0, 8534563520),
                                                   (40, 163, 47, 3, 0, 8534572896),
                                                   (253, 0, 0, 0, 228, 6784213859),
                                                   (255, 0, 0, 0, 26086, 271120),
                                                   (252, 0, 0, 0, 0, 1407380519721)],
                                                  dtype=hit_dtype)

        self.expected_broken_hit_data = np.array([(60, 175, 56, 5, 0, 8534559536),
                                                  (103, 71, 52, 60, 0, 8534563520),
                                                  (104, 71, 52, 58, 0, 8534563520),
                                                  (40, 163, 47, 3, 0, 8534572896),
                                                  (253, 0, 0, 0, 228, 6784213859),
                                                  (255, 0, 0, 0, 26086, 271120)],
                                                 dtype=hit_dtype)

    def test_correct_data(self):
        my_interpreter = interpreter.RawDataInterpreter()
        hit_data, errors = my_interpreter.interpret_data(self.correct_raw_data)

        np.testing.assert_array_equal(hit_data, self.expected_correct_hit_data)
        self.assertEqual(errors, 0)

    def test_broken_data(self):
        my_interpreter = interpreter.RawDataInterpreter()
        hit_data, errors = my_interpreter.interpret_data(self.broken_raw_data)

        np.testing.assert_array_equal(hit_data, self.expected_broken_hit_data)
        self.assertEqual(errors, 2)


if __name__ == "__main__":
    unittest.main()
