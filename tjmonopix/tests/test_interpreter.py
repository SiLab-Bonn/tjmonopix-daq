import unittest
import numpy as np
from tjmonopix.analysis import interpreter
from hypothesis import given
import hypothesis.extra.numpy as nps

@unittest.skip
class TestInterpreter(unittest.TestCase):
    @given(nps.arrays(dtype=np.uint32, shape=4))
    def test_raw_interpreter(self, raw_data):
        # TODO: produce useful raw data with hypothesis
        raw_data = np.array([84085159, 423584740, 754974721, 805306368])
        my_interpreter = interpreter.Interpreter()
        data = my_interpreter.run(raw_data)
        self.assertListEqual(data.tolist(), [(78, 38, 40, 6, 0, 6777355840)])


if __name__ == "__main__":
    unittest.main()