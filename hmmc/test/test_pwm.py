from migen import *
from hmmc.output.pwm import Pwm, DeadTime, PulseGuard
import unittest
import inspect
from math import ceil, log2


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


class TestPwm(unittest.TestCase):
    def deadtime_test_setup(self, dut, dt):
        yield dut.input.eq(0)
        yield dut.deadtime.eq(dt)
        for _ in range(2):
            for _ in range(dt * 2 + 4):
                yield dut.input.eq(0)
                yield
            for _ in range(dt * 2 + 4):
                yield
                yield dut.input.eq(1)
        yield

    @passive
    def deadtime_test_check(self, dut, dt):
        dt += 2
        cnt = 0
        first_cycle = True
        last_h_one = 0
        last_l_one = 0
        while True:
            if (yield dut.out_l):
                last_l_one = cnt
            if (yield dut.out_h):
                last_h_one = cnt

            if (yield dut.out_l):
                self.assertGreaterEqual(cnt, last_h_one + dt, msg=f"cnt={cnt}")
            if (yield dut.out_h):
                self.assertGreaterEqual(cnt, last_l_one + dt, msg=f"cnt={cnt}")
            if not first_cycle:
                if (yield dut.input) and cnt >= last_l_one + dt:
                    self.assertEqual((yield dut.out_h), 1, msg=f"cnt={cnt}")
                if not (yield dut.input) and cnt >= last_h_one + dt:
                    self.assertEqual((yield dut.out_l), 1, msg=f"cnt={cnt}")
            else:
                if (yield dut.input):
                    first_cycle = False

            yield
            cnt += 1

    def test_deadtime_zero(self):
        dt = 0
        dut = DeadTime(4)
        run_simulation(dut, [self.deadtime_test_setup(dut, dt), self.deadtime_test_check(dut, dt)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_deadtime_ten(self):
        dt = 10
        dut = DeadTime(ceil(log2(dt)))
        run_simulation(dut, [self.deadtime_test_setup(dut, dt), self.deadtime_test_check(dut, dt)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
