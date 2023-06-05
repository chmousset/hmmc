Mitsubishi ECNM Encoder
=======================

The encoder answers a simple command-response protocol on a 2.5MBps serial link with no parity
but with a simple checksum.
Some reverse engineering work has been documented on project `stmbl <https://github.com/rene-dev/stmbl/blob/master/src/comps/encm.c>`_.

.. wavedrom::

    {signal: [
      {name: 'req', wave:  '131......|.31..', data: ['0x32', '0x32']},
      {name: 'resp', wave: '1.345..61|..345', data: ['0x32', '', 'pos', 'cs', '0x32', '', 'pos']},
      {name: 'txe', wave:  '1.0......|1.0..'},
    ],
    "config": { "hscale": 1 }
    }

.. note::

    - 0x02 and 0x92 commands seem to be used to identify the motor (and/or encoder) type but are currently ignored. It could be interesting to gather the data exchanged with these commands, altough this can be handled externally (eg. in software), as the UART is external to the module.
    - This Module does not provide an interpolated position update between exchange with the encoder (~25kHz). Checksum error should be monitored to detect communication failure and go in a safe mode.


Module: ECNMEncoder
-------------------

This module works on a byte level. It will need to be connected to an external bidirectional UART configured at 2.5Mbauds/s, like `LiteX RS232PHY <https://github.com/enjoy-digital/litex/blob/a1106b997e33c2783a9088bfbc87e34b8b0de54c/litex/soc/cores/uart.py#L153>`_

.. svgbob::
   :align: center

       +----------------------------+
       |         ECNMEncoder        |
       |============================|
    -->|rx                          |
    -->|rx_valid       position[24] |-->
    <--|rx_ready     position_valid |-->
       |                       idle |-->
    <--|tx                 cs_error |-->
    <--|tx_valid                    |
    -->|tx_idle                     |
       +----------------------------+

.. autoclass:: hmmc.input.mitsubishi.ECNMEncoder
    :members:
