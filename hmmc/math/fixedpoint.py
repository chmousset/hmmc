from migen import Signal, Cat, Replicate
from migen.fhdl.structure import _Value


class FloatFixedConverter:
    """Convert floating numbers to m.n fixed-point numbers

    :param nbits: nbits = m+n if unsigned else nbits=m+n+1
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
    :param radix_nbits: how many bits are in the radix part. If ignored, radix_nbits=resolution if
      signed==False, else radix_nbits=resolution-1
    :type radix_nbits: intradix_bits
    """
    def __init__(self, nbits, radix_nbits, signed=False, saturate=False):
        self.nbits = nbits
        self.radix_nbits = radix_nbits
        self.signed = signed
        self.saturate = saturate
        self.two_ex_radix = 2**radix_nbits
        self.two_ex_nbits = 2**nbits
        self.resolution = 1 / 2**radix_nbits
        if signed:
            self.dec_bits = dec_bits = nbits - radix_nbits - 1
            self.range = -1 * 2**dec_bits, 2**dec_bits - self.resolution
        else:
            self.dec_bits = dec_bits = nbits - radix_nbits
            self.range = 0, 2**(nbits - radix_nbits) - self.resolution
        self.two_ex_dec = 2**dec_bits

    def convert_float(self, value_f):
        """convert a float to a m.n Fixed Point (integer) value

        :param value: value to convert
        :type value: float of list(float)
        """
        if isinstance(value_f, list):
            return [self.convert_float(f) for f in value_f]
        elif isinstance(value_f, float):
            # Calculate min and max (intermediate) integer range
            if self.signed:
                min_value = -1 * 2**(self.nbits - 1)
                max_value = 2**(self.nbits - 1) - 1
            else:
                min_value = 0
                max_value = 2**self.nbits - 1
            value_int = round(value_f * self.two_ex_radix)
            if self.saturate:
                value_int = max(value_int, min_value)
                value_int = min(value_int, max_value)
            elif value_int > max_value or value_int < min_value:
                raise ValueError(f"{value_f} converts to {value_int} outside of "
                    f"[{self.range}]")
            if value_int < 0:
                value_int = (((-1 - value_int) ^ -1) & (self.two_ex_nbits - 1)
                             | (self.two_ex_nbits >> 1))
                assert value_int & 2**(self.nbits - 1)
            return value_int
        else:
            raise TypeError("only float and list(float) are supported")

    def convert_int(self, value_int):
        """convert a m.n Fixed Point (integer) value to a float

        :param value: value to convert
        :type value: int of list(int)
        """
        if isinstance(value_int, list):
            return [self.convert_float(f) for f in value_int]
        elif isinstance(value_int, int):
            if self.signed:
                if value_int & 2**(self.nbits - 1):
                    value_int = -2 * self.two_ex_radix + value_int
            return value_int * self.resolution
        else:
            raise TypeError("only int and list(int) are supported")


class FixedPointSignal(Signal):
    def __init__(self, bits_sign=None, radix_nbits=None, **kwargs):
        """m.n Fractional, Fixed point Signal

        :param bits_sign: see ( :class:`migen.fhdl.structure.Signal` )
        :param radix_nbits: how many bits are in the radix portion. Must be positive, and inferior
          than (nbits + 1) if unsigned, or nbits if signed. By default, radix_nbits=nbits which will
          suit a 0.n fractional number
        :type radix_nbits: int

        Other parameters are passed to Signal()
        """
        super().__init__(bits_sign, **kwargs)
        if radix_nbits is None:
            self.radix_nbits = self.nbits - 1 if self.signed else self.nbits
        else:
            assert radix_nbits >= 0
            assert radix_nbits < self.nbits or not self.signed
            assert radix_nbits <= self.nbits
            self.radix_nbits = radix_nbits

    def eq(self, other):
        """Like :meth:`migen.fhdl.structure.Signal.eq`, assign a :class:`_Value` to this signal.

        It will trimm extra radix resolution, and throw an exception if assigned value does not fit
        withing the FixedPointSignal. In that case, the value should be saturated before assigning
        it.
        """
        if isinstance(other, float):
            value_int = round(other * 2**self.radix_nbits)
            return super().eq(value_int)
        if isinstance(other, int):
            return super().eq(other)
        if self.nbits == other.nbits:
            return super().eq(other)
        if self.nbits >= other.nbits:
            return super().eq(other << (self.nbits - other.nbits))

        dec_bits = self.nbits - self.radix_nbits
        if isinstance(other, FixedPointSignal):
            other_radix_nbits = other.radix_nbits
        elif isinstance(other, _Value):
            other.radix_nbits = other.nbits
        else:
            raise Exception(f"{other} cannot be assigned to {self}")
        other_dec_bits = other.nbits - other_radix_nbits
        assert other_dec_bits <= dec_bits
        return super().eq(Cat(Replicate(other[-1], dec_bits - other_dec_bits),  # Sign extension
            other >> (other.radix_nbits - self.radix_nbits)))  # drop extra radix precision
