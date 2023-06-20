Input
=====

Quadrature Encoder Input
------------------------

This type of `incremental encoder <https://en.wikipedia.org/wiki/Incremental_encoder>`_ signaling is very common in industrial and commercial applications due to its simplicity and potentially low latency.

Two signals (A, B) are 50/50 square with 90% phase between each other, which means that transitions should never occur on both signals simultaneously.
Counting transitions is very easy, and 4 increments can be counted for each line of the encoder.

.. wavedrom::

    {signal: [
      {name: 'a', wave:   '0.1.0.1.0.'},
      {name: 'b', wave:   '01.0.1...0'},
      {name: 'cnt', wave: '=======.==', data: ['0', '1', '2', '3', '4', '5', '6', '5', '4']},
    ],
    "config": { "hscale": 1 }
    }

As this is an incremental interface, transmission errors can introduce a lasting error in the position count. For this reason, an index mark is provided by some higher-end encoders. Such a mark is usually present once per turn for rotary encoder (this way we can know the absolute position of the rotating shaft) or either once or every few mm for linear applications.

The index mark is generally valid for a single line, or 2 increment counts. For this reason, it's combined with the A and B signals to ensure it's valid for a single count increment.

.. wavedrom::

    {signal: [
      {name: 'a', wave: '01.0.x.0.1.0.'},
      {name: 'b', wave: '0.1.0.1.0.1.0'},
      {name: 'i', wave: '0.......1.0..'},
      {name: 'cnt', wave: '=====44.=====', data: ['8', '7', '6', '5', '4', '4', '5', '0', '15', '14', '13', '12']},
      {name: 'expected', wave: '=============', data: ['8', '7', '6', '5', '4', '3', '2', '1', '0', '15', '14', '13', '12']},
    ],
    "config": { "hscale": 1 }
    }

We can see here in this example how the index allowed to correct a 4 count error from a missing pulse.

Usage
*****
Create an intance of QEI Module, then connect the a, b and optionally i inputs to the associated FPGA pins. The QEI module already has FF to resynchronize the pin inputs with the global clock.

The position, index_position and index_capture signals can be used directly.

.. note::

   The parent module will have to implement a correction logic when errors are detected with the index pulse. Typically, this can be done by updating an offset when the index_capture signal is '1'.


.. svgbob::
   :align: center

           +----------------------------------+
           |               QEI                |
           |==================================|
    pin -->|a            position[resolution] |-->
    pin -->|b      index_position[resolution] |-->
    pin -->|i                   index_capture |-->
           +----------------------------------+

Module details
**************

.. automodule:: hmmc.input.quadrature
   :members:

Sigma Delta ADC
---------------

Module details
**************

.. automodule:: hmmc.input.sigmadelta
   :members:

Mitsubishi ECNM Encoder
-----------------------

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


Usage
*****

This module works on a byte level. It will need to be connected to an external bidirectional UART configured at 2.5Mbauds/s, such as this:

.. svgbob::
   :align: center

    +----------+   +----------------------------+
    |  UARTRX  |   |         ECNMEncoder        |
    |==========|   |============================|
    |    rx[8] |-->|rx[8]                       |
    | rx_valid |-->|rx_valid       position[24] |-->
    | rx_ready |<--|rx_ready     position_valid |-->
    +----------+   |                       idle |-->
                   |                   cs_error |-->
    +----------+   |                            |
    |  UARTTX  |   |                            |
    +==========+   |                            |
    |    tx[8] |<--|tx[8]                       |
    | tx_valid |<--|tx_valid                    |
    | tx_ready |-->|tx_idle                     |
    +----------+   +----------------------------+


Here is an example using `LiteX RS232PHY <https://github.com/enjoy-digital/litex/blob/a1106b997e33c2783a9088bfbc87e34b8b0de54c/litex/soc/cores/uart.py#L153>`_:

.. code-block:: python

   self.submodules.ecnm = ecnm = ECNMEncoder(fclk)
   self.submodules.uart = uart = RS232PHY(platform.request("uart"), fclk, baudrate=ecnm.baudrate)
   self.comb += [
      uart.tx.data.eq(ecnm.tx),
      uart.tx_valid.data.eq(ecnm.tx_valid),
      ecnm.tx_idle.eq(uart.tx.ready),
      uart.rx.ready.eq(uart.rx.ready),
      ecnm.rx.eq(uart.rx.data),
      ecnm.rx_valid.eq(uart.rx.valid),
   ]


Module details
**************

.. automodule:: hmmc.input.mitsubishi
   :members:
