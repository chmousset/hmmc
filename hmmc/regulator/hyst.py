from migen import Module, Signal, If
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
