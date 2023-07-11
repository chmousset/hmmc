from migen import Module, Signal, Cat
from hmmc.math.fixedpoint import FixedPointSignal


class DeltaSigma(Module):
    """Generates a bit stream at native clock speed.

    :param resolution: resolution of the input data, in bits
    :type resolution: int

    :inputs:
        - **input** ( :class:`migen.fhdl.structure.Signal` (resolution))) - digital value to convert
          to pulse-density

    :outputs:
        - **output** ( :class:`migen.fhdl.structure.Signal` ) - pulse density modulated output
    """
    def __init__(self, resolution):
        self.input = Signal(resolution)
        self.output = Signal()

        # # #
        cnt = Signal(resolution)
        self.sync += [
            Cat(cnt, self.output).eq(cnt + self.input),
        ]


class DeltaSigmaFixedPoint(Module):
    def __init__(self, resolution, signed=False):
        self.input = FixedPointSignal((resolution, signed))
        self.output = Signal()

        # # #

        cnt = Signal(resolution)

        if signed:
            in_unsigned = Signal(resolution)

            self.sync += Cat(cnt, self.output).eq(cnt + in_unsigned)
            self.comb += in_unsigned.eq(self.input + 2**(resolution - 1))
        else:
            self.sync += Cat(cnt, self.output).eq(cnt + self.input)
