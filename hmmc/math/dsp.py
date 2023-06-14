from migen import Module, Signal, Cat, C, value_bits_sign


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
