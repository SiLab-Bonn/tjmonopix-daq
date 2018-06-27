import unittest
import numpy as np
from tjmonopix.analysis import interpreter
from hypothesis import given, settings
import hypothesis.strategies as st


class TestInterpreter(unittest.TestCase):

    @settings(deadline=None, max_examples=100)
    @given(st.integers(0, 63),
           st.integers(0, 445),
           st.integers(0, 63),
           st.integers(0, 63),
           st.integers(0, 1),
           st.integers(0, 2 ** 52 - 1),
           st.integers(0, 2 ** 32 - 1))
    def test_raw_interpreter(self, col, row, le, te, noise, ts, token):
        # Generate tj_data array from input
        tj_data = 0x0
        tj_data |= (noise << 27) 
        tj_data |= (le << 21)
        tj_data |= (te << 15)
        tj_data |= (row << 6)
        tj_data |= (col)
        
        # Generate timestamp data
        ts_data_1 = 0x10000000
        ts_data_1 |= (ts & 0xFFFFFFF)
        ts_data_2 = 0x20000000
        ts_data_2 |= ((ts & 0xFFFFFF0000000) >> 28)
        
        # Generate token data
        token_data = 0x30000000
        token_data |= ((token & 0xFFFFFFF0) >> 4)
        ts_data_2 |= ((token & 0xF) << 24)
        
        raw_data = np.array([tj_data, ts_data_1, ts_data_2, token_data])

        my_interpreter = interpreter.Interpreter()
        data = my_interpreter.run(raw_data)
        self.assertListEqual(data.tolist(), [(2 * col + row // 256, row % 256, le, te, noise, ts << 4)])


if __name__ == "__main__":
    unittest.main()
