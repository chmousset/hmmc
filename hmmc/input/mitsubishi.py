"""Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike
The encoder answers a simple command-response protocol on a 2.5MBps serial link with no parity
but with a simple checksum.
Some reverse engineering work has been documented here:
https://github.com/rene-dev/stmbl/blob/master/src/comps/encm.c
This Module needs a little bit of work to provide a more frequent position update (>25kHz) than
what the serial protocol can provide.

Possible improvements:
0x02 and 0x92 commands seem to be used to identify the motor (and/or encoder) type but are currently
ignored. It could be interesting to gather the data exchanged with these commands, altough this can
be handled externally (eg. in software), as the UART is external to the module.
"""

from migen import Module, Signal, FSM, NextState, NextValue, If
from migen.genlib.misc import WaitTimer


class ECNMEncoder(Module):
    """Mitsubishi serial protocol compatible with OBA17-052 encoder found in  HC-MFS23 and alike.

    This module must be connected to an UART setup to transmit at 2.5Mbps.

    parameters:
    - fclk: clock frequency of the design

    inputs:
    - rx[8]: serial receive data (from UART)
    - rx_valid: serial receive data valid (from UART)
    - tx_idle: uart is not busy sending, TX line is idle (1)

    outputs:
    - tx[8]: serial transmit data (to UART)
    - tx_valid: serial transmit data valid (to UART)
    - rx_ready: ECNMEncoder is ready to receive UART data, and txe should be set to 0.
    - position[24]: position output
    - position_valid: position output valid
    - idle: set to '1' when the encoder does not respond
    - cs_error: '1' when a checksum error is detected
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
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                If(self.rx != self.cmd,
                    NextState("IDLE"),
                ).Else(
                    NextState("RECEIVE_0"),
                    NextValue(cs, cs ^ self.rx),
                ),
            ),
        )
        fsm.act("RECEIVE_0",
            If(timeout.done,
                NextState("IDLE"),
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
                ),
                NextState("IDLE"),
            ),
            self.rx_ready.eq(1),
            If(self.rx_valid,
                NextValue(cs, cs ^ self.rx),
            ),
        )
