from migen import Module, Signal, Cat


class DeltaSigma(Module):
    """Generates a bit stream at native clock speed.

    :param resolution: resolution of the input data, in bits
    :type resolution: int

    :inputs:
        - **input** (*Signal(resolution)*) - digital value to convert to pulse-density

    :outputs:
        - **output** (*Signal()*) - pulse density modulated output
    """
    def __init__(self, resolution):
        self.input = Signal(resolution)
        self.output = Signal()

        # # #
        cnt = Signal(resolution)
        self.sync += [
            Cat(cnt, self.output).eq(cnt + self.input),
        ]
