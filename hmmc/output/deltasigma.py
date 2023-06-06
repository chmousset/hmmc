from migen import Module, Signal, Cat


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
        self.input = Signal(resolution, name="input")
        self.output = Signal(name="output")

        # # #
        cnt = Signal(resolution)
        self.sync += [
            Cat(cnt, self.output).eq(cnt + self.input),
        ]
