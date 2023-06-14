import unittest
import inspect
from migen import Module, Signal, run_simulation
from hmmc.math.dsp import add_signed_detect_overflow


class add_signed_detect_overflow_dut(Module):
    def __init__(self):
        self.A = A = Signal((8, True))
        self.B = B = Signal((8, True))
        self.submodules.add = add_signed_detect_overflow(A, B)
        self.C = self.add.C
        self.overflow = self.add.overflow
        self.underflow = self.add.underflow


class TestMathDspAddSignedDetectOverflow(unittest.TestCase):
    def add_signed_detect_overflow_test(self, dut):
        yield
        values = [10, -10, -120, 120]
        for a in values:
            for b in values:
                c = a + b
                overflown = c
                if c > 127:
                    overflown = c - 256
                if c < -128:
                    overflown = c + 256
                yield dut.A.eq(a)
                yield dut.B.eq(b)
                yield
                dut_c = (yield dut.C)
                assert dut_c == overflown
                assert (yield dut.overflow) == (1 if c > overflown else 0)
                assert (yield dut.underflow) == (1 if c < overflown else 0)
        yield

    def test_math_dsp_add_signed_detect_overflow(self):
        dut = add_signed_detect_overflow_dut()
        run_simulation(dut, [self.add_signed_detect_overflow_test(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
