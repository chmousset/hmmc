"""
Sigma Delta ADC
===============

Sigma delta generators such as the AMC1303 have a couple of advantages compared to other ADCs:
- few signals (CLK + data)
- the output resolution can be decreased at the expense of sampling rate (or the opposite)
- they can be found with built-in isolation
- up to 16bits, >80dB SNR at ~20kHz can usually be reached

They output a single bit pulse-density signal which has to be filtered to convert the analogue value
at the desired resolution.
"""

from migen import Module, Signal, If
from math import log2, ceil, floor


class Sinc3(Module):
    """Sin-3 lowpass filter

    The most common filter for delta-sigma to parallel conversion, because of its good performances
    compared to the logic utilization.

    :param resolution: resolution of the output, in bits
    :type resolution: int

    :inputs:
        - **input** ( :class:`migen.fhdl.structure.Signal` ) - data input
        - **input_valid** ( :class:`migen.fhdl.structure.Signal` ) - data input valid

    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` (resolution))) - filtered output value
        - **output_valid** ( :class:`migen.fhdl.structure.Signal` ) - filtered output value valid
    """
    def __init__(self, resolution):
        self.input = Signal()
        self.input_valid = Signal()
        self.output = Signal(resolution)
        self.output_valid = Signal()


class IIR_lp(Module):
    """Infinite Impulse Response Low-Pass filter

    Very simple low pass filter. Allows for a simple 1-bit to n-bits upscaling of a delta-sigma
    modulated signal.

    :param resolution: resolution of the output, in bits
    :type resolution: int
    :param damping_coef: damping coefficient. The closer to 0, the longer the settling time. ]0; 1[
    :type damping_coef: float

    :inputs:
        - **input** ( :class:`migen.fhdl.structure.Signal` ) - data input
        - **input_valid** ( :class:`migen.fhdl.structure.Signal` ) - data input valid

    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` (resolution))) - filtered output value
        - **output_valid** ( :class:`migen.fhdl.structure.Signal` ) - filtered output value valid
          (always '1')
    """
    def __init__(self, resolution, damping_coef):
        self.input = Signal()
        self.input_valid = Signal()
        self.output = Signal(resolution)
        self.output_valid = Signal()
        assert damping_coef < 1.0
        assert damping_coef > 0.0
        damping_bits = -floor(log2(damping_coef))
        print(damping_bits)
        assert damping_bits > 0
        assert damping_bits < resolution

        # # #

        acc = Signal(resolution * 2, reset=1 << (resolution * 2 - 1))
        self.sync += [
            If(self.input_valid,
                acc.eq(acc - (acc >> damping_bits)
                    + (self.input << (resolution * 2 - damping_bits))),
            )
        ]
        self.comb += [
            self.output.eq(acc[resolution:]),
            self.output_valid.eq(1),
        ]


class SigmaDelta(Module):
    """Sigma-Delta ADC

    This module generates a single clock `clk_out` for multiple sigmadelta modulator ADC `channels`.
    Each of the channels' 1-bit input signal is sampled from `input` on `clk_out` falling edge.
    Each of the channels' `resolution`-bits output data is present in list `input`.

    :param channels: channel count
    :type channels: int
    :param fout:
    :type fout:
    :param fclk: clock frequency
    :type fclk: int
    :param resolution: output resolution of the converted value
    :type resolution: int
    :param filter_type: one of supported_filters
    :type filter_type: str
    :param filter_parameters: pass additional parameters when instanciating the filter.
                              See respective filter

    :inputs:
        - **input** (*list(Signal())*) - all the different inputs

    :outputs:
        - **clk_out** ( :class:`migen.fhdl.structure.Signal` ) - clock driving the sigma delta
          generator
        - **output** (*list(Signal(resolution))*) - converted signals
        - **output_valid** (*list(Signal())*) - converted signals valid

    .. todo::

        Currently, if **output** is not used (as with hysteretic regulators), the associated logic
        will still be created. It might not be optimized out by the toolchain.
        It could be interesting to instanciate the filter only during the finishing pass, giving the
        option not to generate it.
    """
    supported_filters = {
        'sinc3': Sinc3,
        'iir': IIR_lp,
    }

    def __init__(self, channels, fout, fclk, resolution=16, filter_type="iir", **filter_parameters):
        assert filter_type in self.supported_filters

        # IOS
        self.clk_out = Signal(reset=0)
        self.input = [Signal(name=f"input_{i}") for i in range(channels)]
        self.output = [Signal(resolution, name=f"output_{i}") for i in range(channels)]
        self.output_valid = [Signal(name=f"output_{i}_valid") for i in range(channels)]
        self.input_valid = Signal()

        # # #

        # Clock generator
        f_ratio = ceil(fclk / fout / 2)
        input_valid = self.input_valid
        div = Signal(max=f_ratio + 1, reset=0)
        self.sync += [
            If(div == 0,
                div.eq(f_ratio),
                self.clk_out.eq(~self.clk_out)
            ).Else(
                div.eq(div - 1)
            )
        ]
        self.comb += input_valid.eq((div == 0) & (self.clk_out == 1))

        for i in range(channels):
            filter = self.supported_filters[filter_type](resolution, **filter_parameters)
            setattr(self.submodules, f"{filter_type}_{i}", filter)
            self.comb += [
                filter.input.eq(self.input[i]),
                filter.input_valid.eq(input_valid),
                self.output[i].eq(filter.output),
                self.output_valid[i].eq(filter.output_valid),
            ]
