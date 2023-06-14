from migen import Module, Signal, If, NextState, NextValue, FSM, Case, Cat
from migen.fhdl.bitcontainer import bits_for


class Quadrature(Module):
    """transforms up/down signals into Quadrature outputs

    .. note::

        There is no timing check. Normally, if up and down are followed closely, if ever a short
        pulse isn't registered by the receiver, the position should remain unchanged. However, there
        is an extra sensitivity to noise because of that.
        Also, if multiple up or down are too close to each other, the output will change too quickly
        for the receiver to register them properly.

    :inputs:
        - **up** (*Signal()*) - when '1', generate a pulse on `.step` with `.dir` == '1'
        - **down** (*Signal()*) - when '1', generate a pulse on `.step` with `.dir` == '0'

    :outputs:
        - **a** (*Signal()*) - Quadrature output a
        - **b** (*Signal()*) - Quadrature output b
    """
    def __init__(self):
        # inputs
        self.up = Signal(name="up")
        self.down = Signal(name="down")

        # outputs
        self.a = Signal(name="a")
        self.b = Signal(name="b")

        # # #

        quad = Signal(2, reset_less=True)  # reset-less avoid potential increments on reset
        self.comb += [
            self.a.eq(quad[0]),
            self.b.eq(quad[1]),
        ]
        self.sync += Case(Cat(quad, self.down, self.up),
                    {
                    # _   ↑_↓_quad
                        0b1_0_00: quad.eq(0b01),
                        0b1_0_01: quad.eq(0b11),
                        0b1_0_10: quad.eq(0b00),
                        0b1_0_11: quad.eq(0b10),
                        0b0_1_00: quad.eq(0b10),
                        0b0_1_01: quad.eq(0b00),
                        0b0_1_10: quad.eq(0b11),
                        0b0_1_11: quad.eq(0b01),
        })

        # self.sync += [
        #     If(self.up & ~self.down,
        #         If(quad == 0b00,
        #             quad.eq(0b01),
        #         ).Elif(quad == 0b01,
        #             quad.eq(0b11),
        #         ).Elif(quad == 0b10,
        #             quad.eq(0b00),
        #         ).Else( # 0b11
        #             quad.eq(0b10)
        #         )
        #     ).Elif(~self.up & self.down,
        #         If(quad == 0b00,
        #             quad.eq(0b10),
        #         ).Elif(quad == 0b01,
        #             quad.eq(0b00),
        #         ).Elif(quad == 0b10,
        #             quad.eq(0b11),
        #         ).Else( # 0b11
        #             quad.eq(0b01)
        #         )
        #     )
        # ]


class StepDir(Module):
    """transforms up/down signals into Step/Dir outputs

    .. note::

        This module will keep timings for up to +3/-4 'in flight' pulses. If the up/down period is
        lower than period = (3 + pulse_duration * 2 + turnaround_duration), step loss is expected.
        Make sure the period between 3 consecutive up or 3 consecutive down pulses are >= 3 * period

    :param pulse_duration: duration, in clock ticks, of a STEP pulse
    :type pulse_duration: int
    :param turnaround_duration: duration, in clock ticks, between DIR changing and a STEP pulse
    :type turnaround_duration: int

    :inputs:
        - **up** (*Signal()*) - when '1', generate a pulse on `.step` with `.dir` == '1'
        - **down** (*Signal()*) - when '1', generate a pulse on `.step` with `.dir` == '0'
        - **pulse_duration** (*Signal(ceil(log2(pulse_duration)))*) - initialized at
          param `pulse_duration` but can be dynamically configured externally.
        - **turnaround_duration** (*Signal(ceil(log2(turnaround_duration)))*) - initialized at
          param `turnaround_duration` but can be dynamically configured externally.
    :outputs:
        - **step** (*Signal()*)
        - **dir** (*Signal()*)
    """
    def __init__(self, pulse_duration, turnaround_duration):
        # inputs
        self.up = Signal(name="up")
        self.down = Signal(name="down")

        # outputs
        self.step = Signal(name="step")
        self.dir = Signal(name="dir")

        # # #

        pulse_count = Signal(bits_for(pulse_duration), reset=pulse_duration)
        self.pulse_duration = Signal(bits_for(pulse_duration), reset=pulse_duration)
        pulse_wait = Signal()
        pulse_done = Signal()
        self.comb += pulse_done.eq(pulse_count == 0)
        self.sync += [
            If(pulse_wait,
                If(~pulse_done, pulse_count.eq(pulse_count - 1))
            ).Else(pulse_count.eq(self.pulse_duration)),
        ]

        turnaround_count = Signal(bits_for(turnaround_duration), reset=turnaround_duration)
        self.turnaround_duration = Signal(bits_for(turnaround_duration), reset=turnaround_duration)
        turnaround_wait = Signal()
        turnaround_done = Signal()
        self.comb += turnaround_done.eq(turnaround_count == 0)
        self.sync += [
            If(turnaround_wait,
                If(~turnaround_done, turnaround_count.eq(turnaround_count - 1))
            ).Else(turnaround_count.eq(self.turnaround_duration)),
        ]

        pulses = Signal((3, True))  # up to +3/-4 pulses can be in flight
        step_done = Signal()
        self.sync += [
            Case(Cat(step_done, self.dir, self.down, self.up),
                {
                # _   ↑_↓_dir_step_done
                    0b0_0_0_1: pulses.eq(pulses + 1),  # neg step done
                    0b0_0_1_1: pulses.eq(pulses - 1),  # pos step done
                    0b1_0_0_1: pulses.eq(pulses + 2),  # neg step done, up
                    0b1_0_1_1: pulses.eq(pulses),  # pos step done, up
                    0b0_1_0_1: pulses.eq(pulses),  # neg step done, down
                    0b0_1_1_1: pulses.eq(pulses - 2),  # pos step done, down
                    0b1_0_0_0: pulses.eq(pulses + 1),  # up
                    0b0_1_0_0: pulses.eq(pulses - 1),  # down
                    0b1_0_1_0: pulses.eq(pulses + 1),  # up
                    0b0_1_1_0: pulses.eq(pulses - 1),  # down
                }
            ),
        ]

        self.submodules.fsm = fsm = FSM("IDLE")
        fsm.act("IDLE",
            pulse_wait.eq(1),
            If((pulses < 0) & pulse_done,
                pulse_wait.eq(0),
                If(self.dir,
                    NextValue(self.dir, ~self.dir),
                    NextState("TURNAROUND"),
                ).Else(
                    NextState("STEP_PULSE"),
                ),
            ).Elif((pulses > 0) & pulse_done,
                pulse_wait.eq(0),
                If(~self.dir,
                    NextValue(self.dir, ~self.dir),
                    NextState("TURNAROUND"),
                ).Else(
                    NextState("STEP_PULSE"),
                ),
            ),
        )
        fsm.act("TURNAROUND",
            turnaround_wait.eq(1),
            If(turnaround_done,
                NextState("IDLE"),
            )
        )
        fsm.act("STEP_PULSE",
            self.step.eq(1),
            pulse_wait.eq(~pulse_done),
            If(pulse_done,
                NextValue(self.step, 0),
                NextState("IDLE"),
                step_done.eq(1),
            )
        )
