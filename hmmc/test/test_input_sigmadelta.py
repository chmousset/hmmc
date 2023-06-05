import unittest
import inspect
from hmmc.input.sigmadelta import SigmaDelta
from migen import run_simulation, passive


class TestSigmaDelta(unittest.TestCase):
    @passive
    def sigmadelta_gen_input(self, dut, chan: int, resolution: int, value: int):
        cnt = 0
        resolution = 2**resolution
        old_clk = (yield dut.clk_out)
        while True:
            if (yield dut.clk_out) & ~old_clk:
                cnt += value
                if cnt > resolution:
                    yield dut.input[chan].eq(1)
                    cnt -= resolution
                else:
                    yield dut.input[chan].eq(0)
            old_clk = (yield dut.clk_out)
            yield

    def sigmadelta_check_value(self, dut, chan: int, value: int, tolerance: int,
                               settling_time: int):
        adc = None
        for _ in range(settling_time):
            yield
        for _ in range(settling_time):
            if (yield dut.output_valid[chan]):
                adc = (yield dut.output[chan])
                break
            yield
        if adc is None:
            raise Exception(f"Timedout after {settling_time} cycles")
        self.assertGreaterEqual(value + tolerance, adc)
        self.assertGreaterEqual(adc, value - tolerance)

    def test_output_deltasigma(self):
        resolution = 8
        max_range = 2**resolution
        for damping in [0.1, 0.01]:
            settling_time = int(30 / damping)
            tolerance = int(max_range * damping * 1.5)
            for value in [int(max_range * v) for v in [0.1, 0.3, 0.5, 0.7, 0.9]]:
                dut = SigmaDelta(channels=1, fout=10E6, fclk=20E6, resolution=resolution,
                    filter_type="iir", damping_coef=damping)
                print(f"Checking DeltaSigma gen for damping {damping}, value {value}")
                run_simulation(dut, [
                    self.sigmadelta_gen_input(dut, 0, resolution, value),
                    self.sigmadelta_check_value(dut, 0, value, tolerance, settling_time)],
                    vcd_name=inspect.stack()[0][3] + f"_d{damping}_{value}.vcd")
