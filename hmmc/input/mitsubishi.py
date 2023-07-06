"""Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike
"""

from migen import Module, Signal, FSM, NextState, NextValue, If
from migen.genlib.misc import WaitTimer
from hmmc.math.fixedpoint import FixedPointSignal


class ECNMEncoder(Module):
    """Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike.

    This module must be connected to an UART setup to transmit at 2.5Mbps.

    :param fclk: clock frequency of the design
    :type fclk: int

    :inputs:
        - **rx** ( :class:`migen.fhdl.structure.Signal` (8))) - serial receive data (from UART)
        - **rx_valid** ( :class:`migen.fhdl.structure.Signal` ) - serial receive data valid (from
          UART)
        - **tx_idle** ( :class:`migen.fhdl.structure.Signal` ) - uart is not busy sending, TX line
          is idle (1)

    :outputs:
        - **tx** ( :class:`migen.fhdl.structure.Signal` (8))) - serial transmit data (to UART)
        - **tx_valid** ( :class:`migen.fhdl.structure.Signal` ) - serial transmit data valid (to
          UART)
        - **rx_ready** ( :class:`migen.fhdl.structure.Signal` ) - ECNMEncoder is ready to receive
          UART data, and txe should be
          set to 0
        - **txe** ( :class:`migen.fhdl.structure.Signal` ) - RS485 Transmit Enable control
        - **position** ( :class:`migen.fhdl.structure.Signal` (24))) - position output
        - **position_valid** ( :class:`migen.fhdl.structure.Signal` ) - position output valid
        - **error** ( :class:`migen.fhdl.structure.Signal` ) - set to '1' when any error happens
        - **critical_error** ( :class:`migen.fhdl.structure.Signal` ) - set to '1' on two
          consecutive errors
        - **cs_error** ( :class:`migen.fhdl.structure.Signal` ) - '1' when a checksum error is
          detected
    """

    baudrate = 2500000
    cmd = 0x32

    def __init__(self, fclk):
        # inputs
        self.rx = Signal(8)
        self.rx_valid = Signal()
        self.tx_idle = Signal()

        # outputs
        self.tx = Signal(8, reset=self.cmd)
        self.tx_valid = Signal()
        self.rx_ready = Signal()
        self.txe = Signal(reset=1)
        self.position = Signal(24, reset_less=True)
        self.position_valid = Signal()
        self.cs_error = Signal()
        self.error = Signal()
        self.critical_error = Signal()
        self.shaft_position = FixedPointSignal(24)
        self.shaft_position_valid = self.position_valid

        # # #

        self.comb += self.shaft_position.eq(self.position)

        # we consider line silent if we waited 11 tbit without activity
        self.submodules.timeout = timeout = WaitTimer(1 + int(13 * fclk / self.baudrate))
        self.comb += [
            timeout.wait.eq(~self.rx_valid & ~timeout.done),
        ]

        cs = Signal(8, reset_less=True)
        error = Signal()
        self.submodules.fsm = fsm = FSM("IDLE")
        fsm.act("IDLE",
            NextValue(self.txe, 1),
            If(timeout.done,
                NextState("SEND_CMD"),
                timeout.wait.eq(0),  # reset timer
                NextValue(cs, 0),  # reset checksum
            ),
        )
        fsm.act("SEND_CMD",
            self.tx_valid.eq(1),
            If(self.tx_idle,
                NextState("RECEIVE_CMD"),
            ),
        )
        fsm.act("RECEIVE_CMD",
            If(~self.tx_idle,
                timeout.wait.eq(0),  # reset the counter while sending the command
            ).Else(
                NextValue(self.txe, 0),
            ),
            If(timeout.done,
                NextState("RECOVERY"),
                error.eq(1),
            ),
            self.rx_ready.eq(self.tx_idle),
            If(self.rx_valid & self.rx_ready,
                If(self.rx != self.cmd,
                    NextState("RECOVERY"),
                    error.eq(1),
                ).Else(
                    NextState("RECEIVE_0"),
                    NextValue(cs, cs ^ self.rx),
                ),
            ),
        )
        fsm.act("RECEIVE_0",
            If(timeout.done,
                NextState("RECOVERY"),
                error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_1"),
                NextValue(cs, cs ^ self.rx),
            ),
        )
        fsm.act("RECEIVE_1",
            If(timeout.done,
                NextState("RECOVERY"),
                error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_2"),
                NextValue(cs, cs ^ self.rx),
                NextValue(self.position, self.rx),
            ),
        )
        fsm.act("RECEIVE_2",
            If(timeout.done,
                NextState("RECOVERY"),
                error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_3"),
                NextValue(cs, cs ^ self.rx),
                NextValue(self.position[8:16], self.rx),
            ),
        )
        fsm.act("RECEIVE_3",
            If(timeout.done,
                NextState("RECOVERY"),
                error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_END"),
                NextValue(cs, cs ^ self.rx),
                NextValue(self.position[16:], self.rx),
            ),
        )
        fsm.act("RECEIVE_END",
            # TODO: check that we received the correct amount of bytes?
            If(timeout.done,
                If(cs == 0,  # cs should be 0 if we xor data plus checksum
                    self.position_valid.eq(1),
                ).Else(
                    self.cs_error.eq(1),
                    error.eq(1),
                ),
                NextState("IDLE"),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextValue(cs, cs ^ self.rx),
            ),
        )
        fsm.act("RECOVERY",
            NextValue(self.txe, 0),
            If(timeout.done,
                NextState("IDLE"),
            ),
        )

        error_cnt = Signal()
        self.sync += [
            If(error,
                If(error_cnt == 1,
                    self.critical_error.eq(1),
                ).Else(
                    error_cnt.eq(error_cnt + 1),
                ),
            ).Elif(self.position_valid,
                error_cnt.eq(0),
                self.critical_error.eq(0),
            ),
        ]
