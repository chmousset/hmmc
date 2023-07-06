from migen import Module, Signal, If, NextState, NextValue, FSM
from migen.fhdl.structure import _Value


class WaitTimer(Module):
    def __init__(self, time: _Value, resolution=None):
        resolution if resolution is not None else time.nbits
        self.done = Signal()
        self.wait = Signal()

        # # #

        count = Signal(resolution)
        self.comb += self.done.eq(count == 0)
        self.sync += \
            If(self.wait,
                If(~self.done, count.eq(count - 1))
            ).Else(count.eq(time))


class DeadTimeComplementary(Module):
    """Dead-time insertion, complementary inputs.

    This module takes a two inputs, and creates two outputs which are set to 0 during the deadtime,
    or if both inputs are high.

    :param resolution: size of the counter in bits
    :type resolution: int
    :param default_deadtime: default deadtime, if `deadtime` is not controlled externally
    :type default_deadtime: int

    :inputs:
        - **in_h** ( :class:`migen.fhdl.structure.Signal` ): controls `out_h`
        - **in_l** ( :class:`migen.fhdl.structure.Signal` ): controls `out_l`
        - **deadtime** ( :class:`migen.fhdl.structure.Signal` (resolution)): deadtime duration is
          'deadtime' + 1 clk cycle.

    :outputs:
        - **out_h** ( :class:`migen.fhdl.structure.Signal` ): is '1' if `in_h & ~in_l` and deadtime
          elapsed
        - **out_l** ( :class:`migen.fhdl.structure.Signal` ): is '1' `~in_h & in_l` and deadtime
          elapsed
    """
    def __init__(self, resolution: int, default_deadtime=0):
        self.in_h = Signal()
        self.in_l = Signal()
        self.deadtime = Signal(resolution, reset=default_deadtime)
        self.out_h = Signal()
        self.out_l = Signal()

        self.submodules.wait = wait = WaitTimer(self.deadtime)
        self.submodules.fsm = fsm = FSM("HIZ")
        fsm.act("HIZ",
            wait.wait.eq(1),
            If(wait.done,
                If(self.in_h & ~self.in_l,
                    NextState("HI"),
                    wait.wait.eq(0),
                ).Elif(~self.in_h & self.in_l,
                    NextState("LO"),
                    wait.wait.eq(0),
                ),
            ),
        )
        fsm.act("HI",
            If(~(self.in_h & ~self.in_l),
                NextState("HIZ"),
            ),
        )
        fsm.act("LO",
            If(~(~self.in_h & self.in_l),
                NextState("HIZ"),
            ),
        )


class DeadTime(Module):
    """Dead-time insertion.

    This module takes a single input, and creates two outputs, `out_h` and `out_l`.
    `out_h` has the same sign as `input`, while `out_l` is inverted.

    :param resolution: size of the counter in bits
    :type resolution: int

    :inputs:
        - **input** ( :class:`migen.fhdl.structure.Signal` ): typically from Pwm().output
        - **deadtime** ( :class:`migen.fhdl.structure.Signal` (resolution)): deadtime duration is
          'deadtime' + 1 clk cycle.

    :outputs:
        - **out_h** ( :class:`migen.fhdl.structure.Signal` ): is '1' when input == '1' and deadtime
          elapsed
        - **out_l** ( :class:`migen.fhdl.structure.Signal` ): is '1' when input == '0' and deadtime
          elapsed
    """
    def __init__(self, resolution: int, default_deadtime=0):
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

    :param resolution: size of the counter in bits
    :type resolution: int
    :param settings_sync: if True, PWM settings are updated once per cycle. Ensures no glitch can
        appear on the output
    :type settings_sync: bool

    :inputs:
        - **input** ( :class:`migen.fhdl.structure.Signal` ): typically Pwm().output
        - **min_pulse** ( :class:`migen.fhdl.structure.Signal` (resolution))): min pulse duration
        - **max_pulse** ( :class:`migen.fhdl.structure.Signal` (resolution))): max pulse duration

    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` ): pulse-guarded signal
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
    :param sync_update: update the duty cycles once per cycle. Avoid multiple transitions during a
                        single period.
    :type sync_update: bool
    :param phase: the pwm output can be delayed by `phase` clk cycles. This is useful to stagger
                  multiple Pwm outputs and reduce EMIs
    :type phase: int

    :inputs:
        - **period** ( :class:`migen.fhdl.structure.Signal` (resolution))): length of the entire PWM
          cycle
        - **duty_cycle** ( :class:`migen.fhdl.structure.Signal` (resolution))): length of the '1'
          output state. If 0, output stays
          at 0 all the time.
        - **center_mode** ( :class:`migen.fhdl.structure.Signal` ): if '1', the PWM counter will
          count up and down

    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` ): PWM output
        - **up_cnt** ( :class:`migen.fhdl.structure.Signal` ): in center mode, '1' when the counter
          is incrementing
        - **cycle_update** ( :class:`migen.fhdl.structure.Signal` ): '1' for 1 clk tick, once per
          PWM period
    """
    def __init__(self, resolution: int, sync_update=False, phase=0):
        self.period = Signal(resolution)
        self.duty_cycle = Signal(resolution)
        self.center_mode = Signal()

        self.output = Signal()
        self.up_cnt = Signal(reset=1)
        self.cycle_update = Signal()

        # # #

        cnt = Signal(resolution, reset=phase)  # internal counter

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
