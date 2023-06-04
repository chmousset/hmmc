import unittest
import inspect
from math import floor
from hmmc.output.deltasigma import DeltaSigma
from migen import run_simulation, passive
from random import random


class TestDeltaSigma(unittest.TestCase):
    def deltasigma_test_setup(self, dut, value):
        yield dut.input.eq(value)
        yield

    def deltasigma_check_value(self, dut, value, integration_duration):
        int_out = 0
        for _ in range(integration_duration):
            yield
            int_out += (yield dut.output)
        assert value >= (int_out / integration_duration - 1) * 2**(dut.input.nbits)
        assert value <= (int_out / integration_duration + 1) * 2**(dut.input.nbits)

    @passive
    def deltasigma_check_pulse_duration(self, dut, value):
        input_range = 2**dut.input.nbits
        max_duration = max(value - input_range, input_range - value)
        cnt = 0
        prev_value = (yield dut.output)
        while True:
            if prev_value != (yield dut.output):
                prev_value = (yield dut.output)
                self.assertGreaterEqual(max_duration + 1, cnt)
                cnt = 1
            else:
                cnt += 1
            yield

    def test_deltasigma_rnd(self):
        resolution = 8
        max_range = 2**8
        for _ in range(10):
            dut = DeltaSigma(resolution)
            value = floor(random() * max_range)
            print(f"Checking DeltaSigma gen for value {value}")
            run_simulation(dut, [
                self.deltasigma_test_setup(dut, value),
                self.deltasigma_check_value(dut, value, 100),
                self.deltasigma_check_pulse_duration(dut, value)],
                vcd_name=inspect.stack()[0][3] + f"_{value}.vcd")
