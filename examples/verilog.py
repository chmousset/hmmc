#!/usr/bin/env python3

from migen import Module, Signal
from migen.fhdl.verilog import convert
from hmmc.output.pwm import Pwm, DeadTime


class Top(Module):
    def __init__(self, resolution=10):
        # ios of the toplevel Verilog module to generate
        self.duty_cycle = Signal(resolution)
        self.out_l = Signal()
        self.out_h = Signal()

        # Simple PWM generator.
        self.submodules.pwm = pwm = Pwm(resolution=11)

        # Dead time insertion
        self.submodules.dt = dt = DeadTime(resolution=5)

        self.comb += [
            pwm.period.eq(2**resolution - 1),
            pwm.duty_cycle.eq(self.duty_cycle),
            dt.input.eq(pwm.out),
            self.out_l.eq(dt.out_l),
            self.out_h.eq(dt.out_h),
            dt.deadtime.eq(20),
        ]


if __name__ == '__main__':
    m = Top()
    convert(m, ios={m.duty_cycle, m.out_l, m.out_h}).write("build/pwm.v")
