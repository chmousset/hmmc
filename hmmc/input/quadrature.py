from migen import Module, Signal, Cat, If, Case


class QEI(Module):
    """Quadrature Ecoder Interface
    reads the A, B outputs of a quadrature encoder, and cound position.
    Optionally, can also montitor an Index input and copy the position value when the index postion
    is reached.

    :param resolution: resolution in bits for the position counter
    :type resolution: int
    :param used_index: is True, use the i input to capture index position
    :type used_index: bool

    :inputs:
        - **a** (*Signal()*) - quadrature input a
        - **b** (*Signal()*) - quadrature input b
        - **i** (*Signal()*) - index input, used is use_index is True

    :outputs:
        - **position** (*Signal(resolution)*) - position retreived from the quadrature input
        - **index_position** (*Signal(resolution)*) - captured position at last index mark
        - **index_capture** (*Signal()*) - '1' when the encoder is at the index mark
    """
    def __init__(self, resolution: int, used_index=False):
        """Construct a :obj:`QEI` object.

        Arguments
        ---------

        resolution (:obj:`int`): resolution in bits for the position counter
        used_index (:obj:`bool`): is True, use the i input to capture index position
        """
        self.a = Signal()
        self.b = Signal()
        self.i = Signal()
        self.position = cnt = Signal(resolution, reset_less=True)
        self.index_position = Signal(resolution)

        # # #

        next_cnt = Signal(resolution)

        a_f = Signal(3)
        b_f = Signal(3)
        a = Signal()
        b = Signal()
        self.comb += [
            a.eq(a_f[0]),
            b.eq(b_f[0]),
        ]
        self.sync += [
            a_f.eq(Cat(a_f[1:], self.a)),
            b_f.eq(Cat(b_f[1:], self.b)),
        ]

        self.sync += [
            Case(Cat(b_f[0:2], a_f[0:2]), {
                0b1000: next_cnt.eq(cnt + 1),
                0b1110: next_cnt.eq(cnt + 1),
                0b0111: next_cnt.eq(cnt + 1),
                0b0001: next_cnt.eq(cnt + 1),
                0b0010: next_cnt.eq(cnt - 1),
                0b1011: next_cnt.eq(cnt - 1),
                0b1101: next_cnt.eq(cnt - 1),
                0b0100: next_cnt.eq(cnt - 1)}
            )
        ]

        self.sync += [
            cnt.eq(next_cnt),
        ]

        if used_index:
            i_f = Signal(3)
            i = Signal()
            self.sync += [
                i_f.eq(Cat(self.i, i_f[0:-1])),
            ]
            self.comb += [
                i.eq(i_f[0]),
            ]

            self.sync += [
                If(i & a & b,
                    self.index_position.eq(next_cnt),
                    self.index_capture.eq(1),
                ),
            ]
