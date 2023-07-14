import unittest
import inspect
from hmmc.math.lut import LookupTableFixedPoint
from migen import run_simulation
from random import randrange


class TestMathLUT(unittest.TestCase):
    res = 10
    test_vector = [randrange(0, 2**10 - 1) for _ in range(128)]

    def set_sel(self, dut):
        for i, value in enumerate(self.test_vector):
            yield dut.sel.eq(i)
            yield dut.sel_valid.eq(1)
            yield

    def check_values(self, dut):
        for i, value in enumerate(self.test_vector):
            while (yield dut.output_valid) == 0:
                yield
            self.assertEqual(value, (yield dut.output))
            yield

    def test_math_lut_sync(self):
        dut = LookupTableFixedPoint(self.test_vector, self.res, False, async_read=False)
        run_simulation(dut,
            [self.set_sel(dut), self.check_values(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_math_lut_async(self):
        dut = LookupTableFixedPoint(self.test_vector, self.res, False, async_read=True)
        run_simulation(dut,
            [self.set_sel(dut), self.check_values(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
