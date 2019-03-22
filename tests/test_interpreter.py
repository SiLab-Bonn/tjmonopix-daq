import unittest
import numpy as np
from tjmonopix.analysis import interpreter


class TestInterpreter(unittest.TestCase):
    def setUp(self):
        hit_dtype = [("col", "<u1"), ("row", "<u2"), ("le", "<u1"), ("te", "<u1"), ("cnt", "<u4"),
                     ("timestamp", "<i8"), ("scan_param_id", "<u4")]
        meta_dtype = [("index_start", "<u4"), ("index_stop", "<u4"), ("scan_param_id", "<u4")]

        # Meta data
        self.meta_data_for_correct = np.array([(0, 4, 22), (4, 8, 23), (8, 20, 24), (20, 27, 25)], dtype=meta_dtype)
        self.meta_data_for_broken = np.array([(0, 3, 0), (3, 7, 1), (7, 19, 2), (19, 25, 3)], dtype=meta_dtype)

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

        self.expected_correct_hit_data = np.array([(59, 175, 57, 0, 0, 8534559536, 22),
                                                   (60, 175, 56, 5, 0, 8534559536, 23),
                                                   (103, 71, 52, 60, 0, 8534563520, 24),
                                                   (104, 71, 52, 58, 0, 8534563520, 24),
                                                   (40, 163, 47, 3, 0, 8534572896, 24),
                                                   (253, 0, 0, 0, 228, 6784213859, 25),
                                                   (255, 0, 0, 0, 26086, 271120, 25),
                                                   (251, 0, 0, 0, 0, 1407380519721, 25)],
                                                  dtype=hit_dtype)

        self.expected_broken_hit_data = np.array([(60, 175, 56, 5, 0, 8534559536, 1),
                                                  (103, 71, 52, 60, 0, 8534563520, 2),
                                                  (104, 71, 52, 58, 0, 8534563520, 2),
                                                  (40, 163, 47, 3, 0, 8534572896, 2),
                                                  (253, 0, 0, 0, 228, 6784213859, 3),
                                                  (255, 0, 0, 0, 26086, 271120, 3)],
                                                 dtype=hit_dtype)

    def test_correct_data(self):
        my_interpreter = interpreter.Interpreter()
        hit_data, errors = my_interpreter.interpret_data(self.correct_raw_data, self.meta_data_for_correct)

        print(hit_data)

        np.testing.assert_array_equal(hit_data, self.expected_correct_hit_data)
        self.assertEqual(errors, 0)

    def test_broken_data(self):
        my_interpreter = interpreter.Interpreter()
        hit_data, errors = my_interpreter.interpret_data(self.broken_raw_data, self.meta_data_for_broken)

        np.testing.assert_array_equal(hit_data, self.expected_broken_hit_data)
        self.assertEqual(errors, 2)


if __name__ == "__main__":
    unittest.main()
