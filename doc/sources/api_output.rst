Output
======
Pulse Width Modulator
---------------------

PWM is typically used to modulate voltage applied on inductive loads such as motor phases, as the
inductive load smoothens the current. The average (DC) current flowing through the inductive load is
roughly equivalent as if a DC voltage of Vbus*duty_cycle/period was applied.
The PWM can then be seen as a digital to analog converter.

Contrary to deltasigma modulation, the PWM output frequency reduces with frequency and allows a good
balance between resolution and switching losses in power applications.

Module details
**************

.. automodule:: hmmc.output.pwm
   :members:

Delta Sigma DAC
---------------
Delta Sigma modulators are simple Digital to Analog Converters. It transforms an integer in density of pulses.

.. wavedrom::

   {signal: [
     {name: 'in', wave:  '2...2...2...2...', data: ['0', '1', '2', '3']},
     {name: 'out', wave: '0...10..10101...'},
   ]}

The modulated signal can be directly output on a digital pin, then with a simple RC low pass filter an analog voltage can be generated like so:

.. svgbob::
   :align: center

   --+
     | digital  _____
   F |---------|_____|---o-----> Analog voltage
   P | output     R     _|_
   G |                  ___ C
   A |                   |
     |                  _|_
   --+                  GND

Multiple modulated signals can also be used in the digital domain to be combined, compared or integrated when low logic usage can be traded for increase noise or reduced performance.

.. todo::

   A possible improvement would be to support wider output, enabling the use of R2R resistor ladder to increase the analog resolution and/or bandwidth.


Module details
**************

.. automodule:: hmmc.output.deltasigma
   :members:
