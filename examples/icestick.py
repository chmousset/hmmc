#!/usr/bin/env python3

import argparse
from migen.build.generic_platform import Subsignal, Pins, Misc
from migen import Module, If, Signal
from migen.build.platforms.icestick import Platform
from hmmc.output.pwm import Pwm

_ios = [
    ("pwm", 0,
        Subsignal("out", Pins("GPIO1:0")),
    ),
]


class Top(Module):
    def __init__(self, platform, with_pwm=False):
        platform.add_extension(_ios)

        # Simple PWM generator. Creates a 'breathing' pattern on the LED D1
        if with_pwm:
            self.submodules.pwm = pwm = Pwm(resolution=11)
            self.comb += [
                pwm.period.eq(2047),
                platform.request("user_led", 0).eq(pwm.out),
                platform.request("pwm", 0).out.eq(pwm.out),
            ]
            down = Signal()
            self.sync += [
                If(pwm.cycle_update,
                    If(down,
                        If(pwm.duty_cycle == 0,
                            down.eq(0),
                        ).Else(
                            pwm.duty_cycle.eq(pwm.duty_cycle - 1),
                        ),
                    ).Else(
                        If(pwm.duty_cycle == pwm.period,
                            down.eq(1),
                        ).Else(
                            pwm.duty_cycle.eq(pwm.duty_cycle + 1),
                        ),
                    )
                )
            ]


if __name__ == '__main__':
    def auto_int(x):
        return int(x, 0)
    parser = argparse.ArgumentParser("Icestick NewMot demo")
    parser.add_argument("--build", "-b", action="store_true", help="build the FPGA")
    parser.add_argument("--flash", "-f", action="store_true", help="flash the FPGA")
    parser.add_argument("--pwm", action="store_true", help="Add PWM controller")
    args = parser.parse_args()

    plat = Platform()

    soc = Top(platform=plat,
        with_pwm=args.pwm,
    )

    if args.build:
        plat.build(soc, build_dir="build/icestick")
    if args.flash:
        plat.create_programmer().flash(0, "build/icestick/top.bin")
