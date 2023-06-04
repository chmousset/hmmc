from migen import *
from hmmc.output.pwm import Pwm, DeadTime, PulseGuard
import unittest
import inspect


class TestPwm(unittest.TestCase):
    def pwm_test(self, dut, period, dc):
        cnt = 0
        yield dut.period.eq(period)
        yield dut.duty_cycle.eq(dc)
        self.assertEqual((yield dut.out), 0, msg=f"cnt={cnt}")
        self.assertEqual((yield dut.cycle_update), 1, msg=f"cnt={cnt}")
        yield
        for _ in range(dc):
            self.assertEqual((yield dut.out), 1, msg=f"cnt={cnt}")
            self.assertEqual((yield dut.cycle_update), 1 if cnt % (period + 1) == 0 else 0, msg=f"cnt={cnt}")
            yield
            cnt += 1
        for _ in range(period - dc):
            self.assertEqual((yield dut.out), 0, msg=f"cnt={cnt}")
            self.assertEqual((yield dut.cycle_update), 1 if cnt % (period + 1) == 0 else 0, msg=f"cnt={cnt}")
            yield
            cnt += 1
        yield

    def test_pwm_zero(self):
        dut = Pwm(resolution=8)
        run_simulation(dut, [self.pwm_test(dut, 100, 0)], vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_pwm_hunderd_percent(self):
        dut = Pwm(resolution=8)
        run_simulation(dut, [self.pwm_test(dut, 100, 100)], vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_pwm_over_hunderd_percent(self):
        dut = Pwm(resolution=8)
        run_simulation(dut, [self.pwm_test(dut, 100, 140)], vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_pwm_twenty(self):
        dut = Pwm(resolution=8)
        run_simulation(dut, [self.pwm_test(dut, 100, 20)], vcd_name=inspect.stack()[0][3] + ".vcd")
