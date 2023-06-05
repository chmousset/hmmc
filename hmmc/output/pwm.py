"""
Pulse Width Modulator
=====================

PWM is typically used to modulate voltage applied on inductive loads such as motor phases, as the
inductive load smoothens the current. The average (DC) current flowing through the inductive load is
roughly equivalent as if a DC voltage of Vbus*duty_cycle/period was applied.
The PWM can then be seen as a digital to analog converter.

Contrary to deltasigma modulation, the PWM output frequency reduces with frequency and allows a good
balance between resolution and switching losses in power applications.
"""
from migen import Module, Signal, If, NextState, NextValue, FSM


class DeadTime(Module):
    """Dead-time insertion.

    Switch mode power stage usually need to respect a proper switch-off / switch-on sequence for
    each of the power switches to avoid damage to the hardware.
    By inserting a "dead time" between a power switch turn-off and it's complementary switch
    turn-on, cross-conduction can be avoided.

    This module takes a single input, and creates two outputs, `out_h` and `out_l`.
    `out_h` has the same sign as `input`, while `out_l` is inverted.

    :param resolution: size of the counter in bits
    :type resolution: int

    :inputs:
        - **input** (*Singnal()*): typically from Pwm().output
        - **deadtime** (*Singnal(resolution)*): deadtime duration is 'deadtime' + 1 clk cycle.

    :outputs:
        - **out_h** (*Signal()*): is '1' when input == '1' and deadtime elapsed
        - **out_l** (*Signal()*): is '1' when input == '0' and deadtime elapsed
    """
    def __init__(self, resolution: int):
        self.input = Signal()
        self.deadtime = Signal(resolution)
        self.out_h = Signal()
        self.out_l = Signal()

        # # #

        prev_in = Signal()
        cnt = Signal(resolution, reset=2**resolution - 1)

        self.comb += [
            self.out_h.eq((prev_in == self.input) & (cnt == 0) & self.input),
            self.out_l.eq((prev_in == self.input) & (cnt == 0) & (~self.input)),
        ]

        self.sync += [
            If(prev_in != self.input,
                cnt.eq(self.deadtime)
            ).Elif(cnt,
                cnt.eq(cnt - 1)
            ),
            prev_in.eq(self.input),
        ]


class PulseGuard(Module):
    """Ensure minimum and maximum pulse length are respected.

    This module enables to lenghten or shorten a stream of pulses (such as a PWM or delta-sigma
    modulated signal).
    If the input changes state, the output will stay at this value for at least min_pulse
    If the input does not change for longer than max_pulse, an opposite signal will be generated for
    min_pulse

    This allows filtering of noisy command signal before a switch-mode power stage like a motor
    control power bridge.

    :type resolution: int
    :param resolution: size of the counter in bits
    :param settings_sync: if True, PWM settings are updated once per cycle. Ensures no glitch can
        appear on the output
    :type settings_sync: bool

    :inputs:
        - **input** (*Signal()*): typically Pwm().output
        - **min_pulse** (*Signal(resolution)*): min pulse duration
        - **max_pulse** (*Signal(resolution)*): max pulse duration

    :outputs:
        - **output* (*Signal()*): pulse-guarded signal
    """
    def __init__(self, resolution: int, settings_sync=False):
        self.input = Signal()
        self.min_pulse = Signal(resolution)
        self.max_pulse = Signal(resolution, reset=2**resolution - 1)
        self.output = Signal()

        # # #

        cnt = Signal(resolution)
        prev_out = Signal()

        if settings_sync:
            # min and max are sync'd when cnt == 0
            minp = Signal(resolution)
            maxp = Signal(resolution)
            self.sync += [
                If(cnt == 0,
                    minp.eq(self.min_pulse),
                    maxp.eq(self.max_pulse)
                )
            ]

        else:
            minp = self.min_pulse
            maxp = self.max_pulse

        self.submodules.fsm = fsm = FSM(reset_state="NORM")
        fsm.act("FORCE_MIN",
            self.output.eq(prev_out),
            NextValue(cnt, cnt + 1),
            If(cnt == minp,
                NextState("NORM"),
            ),
        )
        fsm.act("NORM",
            If((prev_out != self.input) | (cnt == maxp),
                NextValue(cnt, 0),
                NextState("FORCE_MIN"),
                NextValue(prev_out, ~prev_out),
                self.output.eq(~prev_out),
            ).Else(
                NextValue(cnt, cnt + 1),
                self.output.eq(self.input),
            ),
        )

        self.sync += prev_out.eq(self.output)


class Pwm(Module):
    """Pulse-Width Modulator.

    Generates a rectangular wave of fixed period. '1'/'0' output ratio = duty_cycle/period

    :param resolution: size of the counter in bits
    :type resolution: int

    :inputs:
        - **period** (*Signal(resolution)*): length of the entire PWM cycle
        - **duty_cycle** (*Signal(resolution)*): length of the '1' output state. If 0, output stays
          at 0 all the time.
        - **center_mode** (*Signal()*): if '1', the PWM counter will count up and down

    :outputs:
        - **output** (*Signal()*): PWM output
        - **up_cnt** (*Signal()*): in center mode, '1' when the counter is incrementing
        - **cycle_update** (*Signal()*): '1' for 1 clk tick, once per PWM period
    """
    def __init__(self, resolution: int, sync_update=False):
        self.period = Signal(resolution)
        self.duty_cycle = Signal(resolution)
        self.center_mode = Signal()

        self.output = Signal()
        self.up_cnt = Signal(reset=1)
        self.cycle_update = Signal()

        # # #

        cnt = Signal(resolution)                 # internal counter

        if sync_update:
            # update the duty cycle once per cycle
            dc = self.duty_cycle
            duty_cycle = Signal(resolution)
            self.sync += If(self.cycle_update, duty_cycle.eq(dc))
        else:
            duty_cycle = self.duty_cycle

        self.comb += [
            # Cycle sync pulse
            self.cycle_update.eq((cnt == 0) | (self.center_mode & (cnt == duty_cycle))),
            self.output.eq(duty_cycle > cnt),
        ]

        self.sync += [
            If(self.up_cnt,
                # incrementing counter
                If(cnt == self.period,
                    If(self.center_mode,
                        self.up_cnt.eq(0),
                        cnt.eq(cnt - 1)
                    ).Else(
                        cnt.eq(0),
                    )
                ).Else(cnt.eq(cnt + 1)),
            ).Else(
                # decrementing counter
                If(cnt == 0,
                    cnt.eq(1),
                    self.up_cnt.eq(1),
                ).Else(cnt.eq(cnt - 1))
            ),
        ]
