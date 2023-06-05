Quadrature Encoder Input
========================

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

Module: QEI
-----------

.. svgbob::
   :align: center

       +----------------------------------+
       |               QEI                |
       |==================================|
    -->|a            position[resolution] |-->
    -->|b      index_position[resolution] |-->
    -->|i                   index_capture |-->
       +----------------------------------+

.. autoclass:: hmmc.input.quadrature.QEI
    :members:
