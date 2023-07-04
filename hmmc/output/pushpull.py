from migen import Module, Signal, If
from hmmc.output.pwm import Pwm


class PushPull(Module):
    """Push-Pull converted driver

    :param period: half period in clk count. Out frequency = Fclk / period / 2
    :type param: int

    :inputs:
      - **duty_cycle** (*Signal()*): duty cycle. Set to 0 to (period-1)

    :outputs:
      - **out_l** (*Signal()*): pwm output phase
      - **out_h** (*Signal()*): pwm output phase
      - **cycle_update** (*Signal()*): '1' when a new PWM cycle starts. Valid for 1 clock cycle
    """
    def __init__(self, period):
        # outputs
        self.out_l = Signal()
        self.out_h = Signal()
        self.cycle_update = Signal()

        # inputs
        self.duty_cycle = Signal(max=period)

        # # #

        pwm_l = Pwm(self.duty_cycle.nbits)
        pwm_h = Pwm(self.duty_cycle.nbits, phase=period)
        self.submodules += pwm_l, pwm_h
        self.comb += [
            pwm_l.center_mode.eq(1),
            pwm_h.center_mode.eq(1),
            pwm_l.period.eq(period),
            pwm_h.period.eq(period),
            pwm_l.duty_cycle.eq(self.duty_cycle),
            pwm_h.duty_cycle.eq(self.duty_cycle),
            self.out_l.eq(pwm_l.output),
            self.out_h.eq(pwm_h.output),
            self.cycle_update.eq(pwm_l.cycle_update),
        ]


class SoftStart(Module):
    """Gradually update a PWM generator duty cycle

    :param predivisor: change the duty cycle at the maximum every (1 + predivisor) PWM cycles
    :type predivisor: int
    :param max_duty_cycle: Maximum duty cycle the module can handle
    :type param: int

    :inputs:
        - **duty_cycle_setpoint** ( :class:`migen.fhdl.structure.Signal` (resolution)))
        - **cycle_update** ( :class:`migen.fhdl.structure.Signal` ())) - set to 1 when a new PWM
          cycle starts. Generally connected to a Pwm's **duty_cycle**

    :outputs:
        - **duty_cycle_output** ( :class:`migen.fhdl.structure.Signal` (resolution))): connect to a
          Pwm duty_cycle input
        - **done** ( :class:`migen.fhdl.structure.Signal` ())): '1' when
          `duty_cycle_output == duty_cycle_setpoint`
    """

    def __init__(self, predivisor, max_duty_cycle):
        # inputs
        self.duty_cycle_setpoint = Signal(max=max_duty_cycle)
        self.cycle_update = Signal()

        # output
        self.duty_cycle_output = Signal(max=max_duty_cycle)
        self.done = Signal()

        # # #

        prediv_cnt = Signal(max=predivisor, reset=predivisor - 1)

        self.comb += [
            self.done.eq(self.duty_cycle_setpoint == self.duty_cycle_output),
        ]

        self.sync += [
            If(self.cycle_update,
                If(prediv_cnt == 0,
                    prediv_cnt.eq(prediv_cnt.reset),
                    If(self.duty_cycle_output > self.duty_cycle_setpoint,
                        self.duty_cycle_output.eq(self.duty_cycle_output - 1),
                    ).Elif(self.duty_cycle_output < self.duty_cycle_setpoint,
                        self.duty_cycle_output.eq(self.duty_cycle_output + 1),
                    ),
                ).Else(
                    prediv_cnt.eq(prediv_cnt - 1),
                ),
            )
        ]
