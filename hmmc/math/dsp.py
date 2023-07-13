from migen import Module, Signal, Cat, C, value_bits_sign
from hmmc.math.fixedpoint import FixedPointSignal


class add_signed_detect_overflow(Module):
    # TODO: move to hmmc.math
    def __init__(self, A, B):
        A_len, A_sig = value_bits_sign(A)
        B_len, B_sig = value_bits_sign(A)
        assert A_len == B_len and A_sig and B_sig

        # output
        self.C = Signal((A_len, True))
        self.overflow = Signal()
        self.underflow = Signal()

        A_extended = Signal(A_len + 1)
        B_extended = Signal(A_len + 1)
        C_extended = Signal(A_len + 1)

        self.comb += [
            A_extended.eq(Cat(A, A[-1])),
            B_extended.eq(Cat(B, B[-1])),
            C_extended.eq(A_extended + B_extended),
            self.overflow.eq(C_extended[-2:] == C(0b01, 2)),
            self.underflow.eq(C_extended[-2:] == C(0b10, 2)),
            self.C.eq(C_extended[0:-1]),
        ]


class MulFixedPoint(Module):
    """Multiply to Fractional, Fixed Point Signals

    .. note::

        The sign of the operands must be identical
    """
    def __init__(self, bits_sign_a, bits_sign_b, radix_nbits_a=None, radix_nbits_b=None):
        def bits_sign(a):
            if isinstance(a, tuple):
                return a
            elif isinstance(a, Signal):
                return a.nbits, a.signed
            elif isinstance(a, FixedPointSignal):
                return a.nbits, a.signed
            else:
                return a, False

        bits_a, signed_a = bits_sign(bits_sign_a)
        bits_b, signed_b = bits_sign(bits_sign_b)
        assert signed_a == signed_b
        signed = signed_a or signed_b
        self.A = FixedPointSignal((bits_a, signed_a), radix_nbits_a)
        self.B = FixedPointSignal((bits_b, signed_b), radix_nbits_b)
        radix_nbits = self.A.radix_nbits + self.B.radix_nbits
        mul = Signal((bits_a + bits_b, signed))
        self.sync += mul.eq(self.A * self.B)
        if signed:
            self.C = FixedPointSignal((bits_a + bits_b - 1, signed), radix_nbits=radix_nbits,
                reset_less=True)  # remove duplicate sign bit
            self.comb += Signal.eq(self.C, mul[0:-1])
        else:
            self.C = FixedPointSignal((bits_a + bits_b, signed), radix_nbits=radix_nbits,
                reset_less=True)
            self.comb += Signal.eq(self.C, mul)
