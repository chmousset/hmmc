from migen import Module, Signal, If, FSM, NextState, Cat
from litex.soc.integration.doc import AutoDoc
from hmmc.math.lut import LookupTableFixedPoint
from hmmc.math.dsp import MulFixedPoint
from hmmc.math.misc import Majority
from hmmc.math.fixedpoint import FixedPointSignal
from hmmc.output.deltasigma import DeltaSigmaFixedPoint


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
        self.setpoint = Signal()
        self.feedback = Signal()
        self.hyst_increase = Signal()
        self.hyst_decrease = Signal()
        # Outputs
        self.output = Signal()  # 1 if setpoint > feedback
        self.output_neg = Signal()
        self.slow_decay = Signal()

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


class LutRegulator(Module):
    def __init__(self, n_phases, current_resolution, lut_init, hyst_resolution, hyst_default):
        assert n_phases == len(lut_init)

        # inputs
        self.amplitude = FixedPointSignal((current_resolution, True))
        self.lut_sel = Signal(max=len(lut_init[0]))
        self.lut_sel_valid = Signal()
        self.hyst_increase = Signal()
        self.hyst_decrease = Signal()
        self.feedbacks = Signal(n_phases)
        # Outputs
        self.outputs = [Signal() for _ in range(n_phases)]
        self.complement_output = Signal()

        # All phases that require a regulator
        named_submodules = dict()
        for i, init in enumerate(lut_init):
            named_submodules[f"lut_{i}"] = LookupTableFixedPoint(init, current_resolution, True)
            lut = named_submodules[f"lut_{i}"]
            named_submodules[f"scaling_{i}"] = MulFixedPoint(lut.output, self.amplitude)
            named_submodules[f"setpoint_{i}"] = DeltaSigmaFixedPoint(current_resolution, True)
            named_submodules[f"regulator_{i}"] = HystRegulatorBitSerial(hyst_resolution, hyst_default)
            scaling = named_submodules[f"scaling_{i}"]
            setpoint = named_submodules[f"setpoint_{i}"]
            regulator = named_submodules[f"regulator_{i}"]
            self.comb += [
                lut.sel.eq(self.lut_sel),
                lut.sel_valid.eq(self.lut_sel_valid),
                scaling.A.eq(lut.output),
                scaling.B.eq(self.amplitude),
                setpoint.input.eq(scaling.C),
                regulator.setpoint.eq(setpoint.output),
                regulator.feedback.eq(self.feedbacks[i]),
                regulator.hyst_decrease.eq(self.hyst_decrease),
                regulator.hyst_increase.eq(self.hyst_increase),
                self.outputs[i].eq(regulator.output),
            ]
        for name, sub in named_submodules.items():
            setattr(self.submodules, name, sub)

        # Control the complement phase by inverse majority gate
        self.submodules.majority_gate = majority_gate = Majority(n_phases)
        self.comb += [
            majority_gate.input.eq(Cat(*self.outputs)),
            self.complement_output.eq(~majority_gate.output)
        ]


class HysteresisController(Module):
    """Control hysteresis value based on regulator output.

    This module dynamically controls the hysteresis parameter to respect minimum and maximum
    switching frequency criteria.
    When switching frequency is too high, the hysteresis is increased, and when the frequency is too
    low it's decreased.

    :param resolution: Resolution of the hysteresis parameter.
    :type resolution: int
    :param n_phases: how many phases to monitor. Typically 2 for a 3 phases motor
    :type n_phases: int
    :param fclk: system clock frequency
    :type fclk: int
    :param min_frequency: minimal switching frequency
    :type min_frequency: int
    :param max_frequency: maximal switching frequency
    :type max_frequency: int

    :inputs:
      - **phases** ( :class:`migen.fhdl.structure.Signal`(n_phases) ) - output of the hysteretic
        regulator

    :outputs:
      - **hyst_decrease** ( :class:`migen.fhdl.structure.Signal` ) - signal to decrease the
        hysteresis
      - **hyst_increase** ( :class:`migen.fhdl.structure.Signal` ) - signal to increase the
        hysteresis
    """
    def __init__(self, resolution, n_phases, fclk, min_frequency, max_frequency):
        self.hyst_decrease = Signal()
        self.hyst_increase = Signal()

        # Inputs
        self.phases = phases = Signal(n_phases)

        # outputs
        self.hyst_increase = Signal()
        self.hyst_decrease = Signal()

        # # #

        # Compute the minimum and maximum switching period
        min_period = fclk // max_frequency // n_phases
        max_period = fclk // min_frequency // n_phases

        # switching detection
        switching = Signal()
        prev_phases_states = Signal(n_phases)

        self.comb += If(prev_phases_states != self.phases, switching.eq(1))
        self.sync += prev_phases_states.eq(self.phases)

        # min/max period detection
        cnt = Signal(max=max_period + 1)
        self.sync += [
            If(switching, cnt.eq(0)
            ).Else(
                If(cnt == max_period,
                    cnt.eq(0),
                ).Else(
                    cnt.eq(cnt + 1),
                )
            ),
        ]
        self.comb += [
            self.hyst_decrease.eq(cnt == max_period),
            self.hyst_increase.eq((cnt < min_period) & switching),
        ]
