from migen import Module, Signal, If, FSM, NextState
from litex.soc.integration.doc import AutoDoc


class HystRegulatorBitSerial(Module, AutoDoc):
    """Hysteretic regulator suitable for bitserial feedback and setpoint

    This can generally be used for current or voltage regulation whit a sigma delta ADC.
    The output can then directly be used to control a PWM phase.
    It is not a 'true' hysteretic regulator, in the sense that the error signal is integrated, so
    even the slightest error signal will eventually trigger a change of output signal after a
    certain time.

    :param hyst_resolution: resolution of the hysteresis counter
    :type hyst_resolution: int
    :param hyst_default: default value for the hysteresis
    :type hyst_default: int

    :inputs:
        - **setpoint** ( :class:`migen.fhdl.structure.Signal` ) - Pulse Density setpoint
        - **feedback** ( :class:`migen.fhdl.structure.Signal` ) - Pulse Density feedback
        - **hyst_increase** ( :class:`migen.fhdl.structure.Signal` ) - when '1', increase the
          hysteresis by 1
        - **hyst_decrease** ( :class:`migen.fhdl.structure.Signal` ) - when '1', decrese the
          hysteresis by 1
    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` ) - '1' if the feedback is inferior to
          the setpoint
    """
    def __init__(self, hyst_resolution, hyst_default):
        assert hyst_default >= 1

        # inputs
        self.setpoint = setpoint = Signal()
        self.feedback = feedback = Signal()
        self.hyst_increase = Signal()
        self.hyst_decrease = Signal()
        # Outputs
        self.output = Signal()  # 1 if setpoint > feedback

        # # #

        self.hyst = hyst = Signal(hyst_resolution, reset=hyst_default)
        hyst_cnt = Signal(hyst_resolution, reset=hyst_default)
        self.sync += [
            If((setpoint & ~feedback & self.output) | (~setpoint & feedback & ~self.output),
                If(hyst_cnt < hyst,
                    hyst_cnt.eq(hyst_cnt + 1),
                ).Else(
                    hyst_cnt.eq(hyst),  # handles the case where the hyst is changed on the fly
                ),
            ).Elif((~setpoint & feedback & self.output) | (setpoint & ~feedback & ~self.output),
                If(hyst_cnt == 0,
                    self.output.eq(~self.output),
                    hyst_cnt.eq(hyst),
                ).Else(
                    hyst_cnt.eq(hyst_cnt - 1),
                ),
            ),
            If(self.hyst_increase,
                If(hyst != (2**hyst_resolution - 1),
                    hyst.eq(hyst + 1),
                ),
            ).Elif(self.hyst_decrease,
                If(hyst != 1,
                    hyst.eq(hyst - 1),
                ),
            ),
        ]


class TriHystRegulatorBitSerial(Module, AutoDoc):
    """Three step Hysteretic regulator suitable for bitserial feedback and setpoint

    This regulator is close to the HystRegulatorBitSerial, but makes use of the 'slow decay' mode to
    lower the overall current ripple. This can potentially yield a more efficient and quieter
    current regulation.

    If feedback > setpoint, the internal state will move from "NEG" to "SLOW_DECAY" to "POS".
    If feedback < setpoint, the internal state will move from "POS" to "SLOW_DECAY" to "NEG".

    :param hyst_resolution: resolution of the hysteresis counter
    :type hyst_resolution: int
    :param hyst_default: default value for the hysteresis
    :type hyst_default: int

    :inputs:
        - **setpoint** ( :class:`migen.fhdl.structure.Signal` ) - Pulse Density setpoint
        - **feedback** ( :class:`migen.fhdl.structure.Signal` ) - Pulse Density feedback
        - **hyst_increase** ( :class:`migen.fhdl.structure.Signal` ) - when '1', increase the
          hysteresis by 1
        - **hyst_decrease** ( :class:`migen.fhdl.structure.Signal` ) - when '1', decrese the
          hysteresis by 1
    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` ) - '1' if in "POS" state
        - **output_neg** ( :class:`migen.fhdl.structure.Signal` ) - '1' if in "NEG" state
        - **slow_decay** ( :class:`migen.fhdl.structure.Signal` ) - '1' if in "SLOW_DECAY" state
    """
    def __init__(self, hyst_resolution, hyst_default):
        assert hyst_default >= 1

        # inputs
        self.setpoint = Signal(name="setpoint")
        self.feedback = Signal(name="feedback")
        self.hyst_increase = Signal(name="hyst_increase")
        self.hyst_decrease = Signal(name="hyst_decrease")
        # Outputs
        self.output = Signal(name="output")  # 1 if setpoint > feedback
        self.output_neg = Signal(name="output_neg")
        self.slow_decay = Signal(name="slow_decay")

        # # #

        self.hyst = hyst = Signal(hyst_resolution, reset=hyst_default)
        error_pos = Signal()  # (feedback - setpoint) > 0
        error_neg = Signal()  # (feedback - setpoint) < 0
        hyst_cnt_pos = Signal(hyst_resolution, reset=hyst_default)
        hyst_cnt_neg = Signal(hyst_resolution, reset=hyst_default)
        hyst_cnt_rst = Signal()  # hyst_cnt_pos should be reset
        move_pos = Signal()  # output state will move towards positive (NEG->SLOW->POS)
        move_neg = Signal()  # output state will move towards negative (POW->SLOW->NEG)
        self.comb += [
            error_pos.eq(self.feedback & ~self.setpoint),
            error_neg.eq(~self.feedback & self.setpoint),
        ]
        self.sync += [
            move_neg.eq(0),
            move_pos.eq(0),
            If(hyst_cnt_rst,
                hyst_cnt_neg.eq(hyst),
                hyst_cnt_pos.eq(hyst),
            ).Elif(error_pos,
                If(hyst_cnt_pos > 0,
                    hyst_cnt_pos.eq(hyst_cnt_pos - 1),
                ).Else(
                    move_neg.eq(1),
                ),
                If(hyst_cnt_neg < hyst,
                    hyst_cnt_neg.eq(hyst_cnt_neg),
                ).Else(
                    hyst_cnt_neg.eq(hyst),
                ),
            ).Elif(error_neg,
                If(hyst_cnt_neg > 0,
                    hyst_cnt_neg.eq(hyst_cnt_neg - 1),
                ).Else(
                    move_pos.eq(1),
                ),
                If(hyst_cnt_pos < hyst,
                    hyst_cnt_pos.eq(hyst_cnt_pos),
                ).Else(
                    hyst_cnt_pos.eq(hyst),
                ),
            ),
        ]

        self.submodules.fsm = fsm = FSM("SLOW_DECAY")
        fsm.act("SLOW_DECAY",
            self.slow_decay.eq(1),
            If(move_neg,
                NextState("NEG"),
                hyst_cnt_rst.eq(1),
            ).Elif(move_pos,
                NextState("POS"),
                hyst_cnt_rst.eq(1),
            ),
        )
        fsm.act("NEG",
            self.output_neg.eq(1),
            If(move_pos,
                NextState("SLOW_DECAY"),
                hyst_cnt_rst.eq(1),
            ),
        )
        fsm.act("POS",
            self.output.eq(1),
            If(move_pos,
                NextState("SLOW_DECAY"),
                hyst_cnt_rst.eq(1),
            ),
        )
