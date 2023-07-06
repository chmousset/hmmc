from migen import Module, Signal, Cat, C, value_bits_sign
from migen.fhdl.structure import _Value
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
    def __init__(self, bits_sign_a, bits_sign_b):
        if isinstance(bits_sign_a, int):
            bits_sign_a = (bits_sign_a, False)
        if isinstance(bits_sign_b, int):
            bits_sign_b = (bits_sign_b, False)

        if isinstance(bits_sign_a, _Value):
            bits_a, signed_a = bits_sign_a.nbits, bits_sign_a.signed
        elif isinstance(bits_sign_a, tuple):
            bits_a, signed_a = bits_sign_a
        else:
            bits_a, signed_a = bits_sign_a, False
        if isinstance(bits_sign_b, _Value):
            bits_b, signed_b = bits_sign_b.nbits, bits_sign_b.signed
        elif isinstance(bits_sign_b, tuple):
            bits_b, signed_b = bits_sign_b
        else:
            bits_b, signed_b = bits_sign_b, False
        self.A = FixedPointSignal((bits_a, signed_a))
        self.B = FixedPointSignal((bits_b, signed_b))
        mul = Signal((bits_a + bits_b, signed_a or signed_b))
        self.C = FixedPointSignal((bits_a + bits_b, signed_a or signed_b))

        self.sync += [
            mul.eq(self.A * self.B),
        ]
        self.comb += [
            self.C.eq(mul),
        ]
