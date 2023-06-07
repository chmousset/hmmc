from math import log2, ceil
from migen import Module, Signal, Memory
from hmmc.math.fixedpoint import FixedPointSignal


class LookupTableFixedPoint(Module):
    """Synchronous or Asynchronous LUT
    :param init: values of the LUT. Use :class:`.FloatFixedConverter` output to convert from float
                 values.
    :type init: list(int)
    :param resolution: resolution of the output
    :type resolution: int
    :param async_read: output of the LUT is immedately available. **Please be aware that this will
                       prevent the LUT to use block RAM in many FPGA architecture**
    :type async_read: bool

    :inputs:
        - **sel** ( :class:`migen.fhdl.structure.Signal` (input_resolution))
        - **sel_valid** ( :class:`migen.fhdl.structure.Signal` ): will be pipelined to
          `output_valid`

    :outputs:
        - **output** ( :class:`.FixedPointSignal` ): out = init[sel]. If async_read=False, out value
          will be valid one clock cycle after sel has been changed.
        - **output_valid** ( :class:`migen.fhdl.structure.Signal` ): is '1' when the output is valid
    """
    def __init__(self, init, resolution, async_read=False):
        # sanity checks
        sample_cnt = len(init)
        input_resolution = ceil(log2(sample_cnt))
        assert (sample_cnt & (sample_cnt - 1) == 0) and sample_cnt != 0  # Power of 2 are supported
        assert min(init) >= 0
        assert max(init) < 2**resolution

        # Input/outputs
        self.sel = Signal(input_resolution)
        self.sel_valid = Signal(name="sel_valid")
        self.output = FixedPointSignal(resolution)
        self.output_valid = Signal(name="output_valid")

        # # #

        self.init = init

        mem = Memory(resolution, sample_cnt, init=init)
        rp = mem.get_port(async_read=async_read)
        self.specials += mem, rp

        self.comb += [
            rp.adr.eq(self.sel),
            self.output.eq(rp.dat_r),
        ]

        if async_read:
            self.comb += self.output_valid.eq(self.sel_valid)
        else:
            self.sync += self.output_valid.eq(self.sel_valid)
