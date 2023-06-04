# Delta Sigma DAC
from migen import Module, Signal, Cat


class DeltaSigma(Module):
    """Delta Sigma DAC

    Very simple modulator. Generates a bit stream at native clock speed.
    """
    def __init__(self, resolution):
        self.input = Signal(resolution)
        self.output = Signal()

        # # #
        cnt = Signal(resolution)
        self.sync += [
            Cat(cnt, self.output).eq(cnt + self.input),
        ]
