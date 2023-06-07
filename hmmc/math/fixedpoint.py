from migen import Module, Signal


class FloatFixedConverter:
    """Convert floating numbers to 0.n fixed-point numbers

    :param resolution: n=resolution
    :type resolution: int
    :param saturate: if True, out-of-range values will be replaced by the min/max of the range. If
                     False, :meth:`convert_float()` out-of-range values will raise a
                     :meth:`ValueError`
    :type saturate: bool
    :param amplitude: amplitude of the float to convert
    :type amplitude: float
    :default amplitude: 1.0
    :param signed: If True, convert a [-amplitude; amplitude[ value to [0; 2^resolution-1]. if
                   False, convert a [0.0; amplitude[ value to [0; 2^resolution-1]
    :type signed: bool
    """
    def __init__(self, resolution, saturate=False, amplitude=1.0, signed=True):
        self.resolution = resolution
        self.saturate = saturate
        self.two_ex_res = 2**resolution
        self.scale = (0.5 / amplitude if signed else 1.0 / amplitude) * self.two_ex_res
        self.signed = signed

    def convert_float(self, value_f):
        """convert a float to a 0.n Fixed Point (integer) value

        :param value: value to convert
        :type value: float of list(float)
        """
        if isinstance(value_f, list):
            return [self.convert_float(f) for f in value_f]
        elif isinstance(value_f, float):
            value_int = round(value_f * self.scale)
            if self.signed:
                max_range = (self.two_ex_res >> 1) - 1
                min_range = -1 * (self.two_ex_res >> 1)
            else:
                max_range = self.two_ex_res - 1
                min_range = 0
            if self.saturate:
                value_int = min(max_range, value_int)
                value_int = max(min_range, value_int)
            elif value_int > max_range or value_int < min_range:
                raise ValueError(f"{value_f} converts to {value_int} outside of "
                    f"[{max_range};{min_range}]")
            if value_int < 0:
                value_int = ((-1 - value_int) ^ -1) & (self.two_ex_res - 1) | (self.two_ex_res >> 1)
            return value_int
        else:
            print(f"type={type(value_f)}")
            raise TypeError("only float and list(float) are supported")

    def convert_int(self, value_int):
        """convert a 0.n Fixed Point (integer) value to a float

        :param value: value to convert
        :type value: int of list(int)
        """
        if isinstance(value_int, list):
            return [self.convert_float(f) for f in value_int]
        elif isinstance(value_int, int):
            if self.signed:
                if value_int & (self.two_ex_res >> 1):
                    value_int = -1 * (self.two_ex_res - value_int)
            return value_int / self.scale
        else:
            raise TypeError("only int and list(int) are supported")


class FixedPointSignal(Signal):
    """Signal with 0.n Fixed Point support"""
    def eq(self, other):
        """Like :meth:`migen.fhdl.structure.Signal.eq`, assign a :class:`_Value` to this signal"""
        if self.nbits == other.nbits:
            return super().eq(other)
        if self.nbits >= other.nbits:
            return self.eq(other << (self.nbits - other.nbits))
        return self.eq(other >> (other.nbits - self.nbits))
