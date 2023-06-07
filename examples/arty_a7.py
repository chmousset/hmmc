import argparse
import subprocess
from migen.build.platforms.arty_a7 import Platform
from migen import Module, If, Signal, ClockDomain, Instance
from migen.genlib.resetsync import AsyncResetSynchronizer
from hmmc.output.pwm import Pwm


class _CRG(Module):
    def __init__(self, platform):
        clk = platform.request("clk100")
        rst_btn = platform.request("user_btn")
        self.clock_domains.cd_sys = ClockDomain("sys")
        self.specials += AsyncResetSynchronizer(self.cd_sys, rst_btn)
        self.specials += Instance("BUFG", i_I=clk, o_O=self.cd_sys.clk)


class Top(Module):
    def __init__(self, platform, with_pwm=False):
        self.submodules += _CRG(platform)

        # Simple PWM generator. Creates a 'breathing' pattern on the LED D1
        if with_pwm:
            resolution = 13
            self.submodules.pwm = pwm = Pwm(resolution=resolution)
            self.comb += [
                pwm.period.eq(2**resolution - 1),
                platform.request("user_led", 0).eq(pwm.output),
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
    parser = argparse.ArgumentParser("Icestick NewMot demo")
    parser.add_argument("--build", "-b", action="store_true", help="build the FPGA")
    parser.add_argument("--load", "-l", action="store_true", help="configure the FPGA")
    parser.add_argument("--flash", "-f", action="store_true", help="flash the FPGA")
    parser.add_argument("--pwm", action="store_true", help="Add PWM controller")
    args = parser.parse_args()

    plat = Platform()

    soc = Top(platform=plat,
        with_pwm=args.pwm,
    )

    if args.build:
        plat.build(soc, build_dir="build/arty_a7")
    if args.load:
        try:
            plat.create_programmer().load_bitstream("build/arty_a7/top.bin")
        except:
            subprocess.run("openFPGALoader -b arty -m build/arty_a7/top.bit")
    if args.flash:
        try:
            plat.create_programmer().flash(0, "build/arty_a7/top.bin")
        except:
            subprocess.run("openFPGALoader -b arty -f build/arty_a7/top.bit")
