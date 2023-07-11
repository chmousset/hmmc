import unittest
import inspect
from math import floor
from hmmc.output.deltasigma import DeltaSigma, DeltaSigmaFixedPoint
from migen import run_simulation, passive
from random import random


class TestDeltaSigma(unittest.TestCase):
    def deltasigma_test_setup(self, dut, value):
        yield dut.input.eq(value)
        yield

    def deltasigma_check_ratio(self, dut, ratio, integration_duration):
        int_out = 0
        yield  # wait setup
        for _ in range(integration_duration):
            yield
            int_out += (yield dut.output)
        self.assertGreaterEqual(ratio, int_out / integration_duration - 1.5 / integration_duration)
        self.assertGreaterEqual(int_out / integration_duration + 1.5 / integration_duration, ratio)

    @passive
    def deltasigma_check_pulse_duration(self, dut, value):
        input_range = 2**dut.input.nbits
        max_duration = max(value - input_range, input_range - value)
        cnt = 0
        prev_value = (yield dut.output)
        yield  # wait setup
        while True:
            if prev_value != (yield dut.output):
                prev_value = (yield dut.output)
                self.assertGreaterEqual(max_duration + 1, cnt)
                cnt = 1
            else:
                cnt += 1
            yield

    def test_output_deltasigma_rnd(self):
        resolution = 8
        max_range = 2**8
        offset = max_range / 2
        for _ in range(10):
            dut = DeltaSigma(resolution)
            value = floor(random() * max_range)
            ratio = value / 2**resolution
            print(f"Checking DeltaSigma gen for value {value}")
            run_simulation(dut, [
                self.deltasigma_test_setup(dut, value),
                self.deltasigma_check_ratio(dut, ratio, 100),
                self.deltasigma_check_pulse_duration(dut, value)],
                vcd_name=inspect.stack()[0][3] + f"_{value}.vcd")

    def s2r(self, signed_value, nbits):
        return (signed_value + 2**(nbits - 1)) / 2**nbits

    def test_output_deltasigma_signed_rnd(self):
        resolution = 8
        max_range = 2**7
        for _ in range(10):
            dut = DeltaSigmaFixedPoint(resolution, True)
            value = floor((random() - 0.5) * max_range)
            print(f"Checking DeltaSigmaSigned gen for value {value}")
            run_simulation(dut, [
                self.deltasigma_test_setup(dut, value),
                self.deltasigma_check_ratio(dut, self.s2r(value, resolution), 257),
                self.deltasigma_check_pulse_duration(dut, self.s2r(value, resolution))],
                vcd_name=inspect.stack()[0][3] + f"_{value}.vcd")
