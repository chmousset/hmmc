"""Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike
"""

from migen import Module, Signal, FSM, NextState, NextValue, If
from migen.genlib.misc import WaitTimer


class ECNMEncoder(Module):
    """Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike.

    This module must be connected to an UART setup to transmit at 2.5Mbps.

    :param fclk: clock frequency of the design
    :type fclk: int

    :inputs:
        - **rx** (*Signal(8)*) - serial receive data (from UART)
        - **rx_valid** (*Signal()*) - serial receive data valid (from UART)
        - **tx_idle** (*Signal()*) - uart is not busy sending, TX line is idle (1)

    :outputs:
        - **tx** (*Signal(8)*) - serial transmit data (to UART)
        - **tx_valid** (*Signal()*) - serial transmit data valid (to UART)
        - **rx_ready** (*Signal()*) - ECNMEncoder is ready to receive UART data, and txe should be
          set to 0
        - **position** (*Signal(24)*) - position output
        - **position_valid** (*Signal()*) - position output valid
        - **error** (*Signal()*) - set to '1' when any error happens
        - **cs_error** (*Signal()*) - '1' when a checksum error is detected
    """

    baudrate = 2500000
    cmd = 0x32

    def __init__(self, fclk):
        # inputs
        self.rx = Signal(8)
        self.rx_valid = Signal()
        self.tx_idle = Signal()

        # outputs
        self.tx = Signal(8)
        self.tx_valid = Signal()
        self.rx_ready = Signal()
        self.position = Signal(24)
        self.position_valid = Signal()
        self.cs_error = Signal()
        self.error = Signal()

        # # #

        # we consider line silent if we waited 11 tbit without activity
        self.submodules.timeout = timeout = WaitTimer(1 + int(13 * fclk / self.baudrate))
        self.comb += [
            timeout.wait.eq(~self.rx_valid),
        ]

        cs = Signal(8)
        self.submodules.fsm = fsm = FSM("IDLE")
        fsm.act("IDLE",
            If(timeout.done,
                NextState("SEND_CMD"),
                timeout.wait.eq(0),  # reset timer
                NextValue(cs, 0),  # reset checksum
            ),
        )
        fsm.act("SEND_CMD",
            self.tx_valid.eq(1),
            self.tx.eq(self.cmd),
            If(~self.tx_idle,
                NextState("RECEIVE_CMD"),
            ),
        )
        fsm.act("RECEIVE_CMD",
            If(self.tx_idle,
                timeout.wait.eq(0),  # reset the counter while sending the command
            ),
            If(timeout.done,
                NextState("IDLE"),
                self.error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                If(self.rx != self.cmd,
                    NextState("IDLE"),
                    self.error.eq(1),
                ).Else(
                    NextState("RECEIVE_0"),
                    NextValue(cs, cs ^ self.rx),
                ),
            ),
        )
        fsm.act("RECEIVE_0",
            If(timeout.done,
                NextState("IDLE"),
                self.error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_1"),
                NextValue(cs, cs ^ self.rx),
            ),
        )
        fsm.act("RECEIVE_1",
            If(timeout.done,
                NextState("IDLE"),
                self.error.eq(1),
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
                NextState("IDLE"),
                self.error.eq(1),
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
                NextState("IDLE"),
                self.error.eq(1),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextState("RECEIVE_END"),
                NextValue(cs, cs ^ self.rx),
                NextValue(self.position[16:], self.rx),
            ),
        )
        fsm.act("RECEIVE_END",
            If(timeout.done,
                If(cs == 0,  # cs should be 0 if we xor data plus checksum
                    self.position_valid.eq(1),
                ).Else(
                    self.cs_error.eq(1),
                    self.error.eq(1),
                ),
                NextState("IDLE"),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextValue(cs, cs ^ self.rx),
            ),
        )
