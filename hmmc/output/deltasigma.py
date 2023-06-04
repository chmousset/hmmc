""" Delta Sigma DAC

Delta Sigma modulators are simple Digital to Analog Converters. It transforms an integer in density
of pulses.
The modulated signal can be directly output on a digital pin, then with a simple RC low pass filter
an analog voltage can be generated.

Possible improvements:
The modulator could easily support wider output, enabling the use of R2R resistor ladder to increase
the analog resolution or bandwidth.
"""
from migen import Module, Signal, Cat


class DeltaSigma(Module):
    """Delta Sigma DAC

    Very simple modulator. Generates a bit stream at native clock speed.

    parameter:
    - resolution: resolution of the input data, in bits

    inputs:
    - input[resolution]: digital value to convert to pulse-density

    outputs:
    - output: pulse density modulated output
    """
    def __init__(self, resolution):
        self.input = Signal(resolution)
        self.output = Signal()

        # # #
        cnt = Signal(resolution)
        self.sync += [
            Cat(cnt, self.output).eq(cnt + self.input),
        ]
