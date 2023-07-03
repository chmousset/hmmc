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

Dead Time
---------

Switch mode power stage usually need to respect a proper switch-off / switch-on sequence for
each of the power switches to avoid damage to the hardware.
By inserting a "dead time" between a power switch turn-off and it's complementary switch
turn-on, cross-conduction can be avoided.

hmmc provides Deadtime insertion modules for both single and complementary inputs.

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
     {name: 'out', wave: '0...10..10101..0'},
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


Step/Dir
--------

Incremental output module driving a digital output pin. Can be used to drive external motor controllers like stepper motor controllers.

With **Step/Dir Output**, the position is incremented on the rising edge of the `step` output, so a certain pulse duration has to be respected. `dir` output setup timing also has to be respected so that the pulses are correctly counted on the receiving end. This is the most common interface for stepper motor drivers.

.. wavedrom::

    {signal: [
      {name: 'up',   wave: '010.10.10..........'},
      {name: 'down', wave: '0.........10.10.10.'},
      {name: 'step', wave: '0..1010.10..1010.10'},
      {name: 'dir',  wave: '0.1........0.......'},
      {name: 'cnt',  wave: '=..=.=..=...=.=..=.', data: ['0', '1', '2', '3', '2', '1', '0']},
    ],
    "config": { "hscale": 1 }
    }


.. svgbob::
   :align: center

           +----------------------------------+
           |             StepDir              |
           |==================================|
    sig -->|up                           step |--> pin
    sig -->|down                          dir |--> pin
           |                                  |
    sig -->|(pulse_duration )                 |
    sig -->|(turnaround_duration )            |
           +----------------------------------+

**Quadrature** output is the opposite of :class:`hpcnc.input.quadrature.QEI`.

.. wavedrom::

    {signal: [
      {name: 'up',   wave: '010.10.10..........'},
      {name: 'down', wave: '0.........10.10.10.'},
      {name: 'a',    wave: '0....1........0....'},
      {name: 'b',    wave: '0.1.....0..1......0'},
      {name: 'cnt',  wave: '=.=..=..=..=..=...=.', data: ['0', '1', '2', '3', '2', '1', '0']},
    ],
    "config": { "hscale": 1 }
    }


.. svgbob::
   :align: center

           +----------------------------------+
           |            Quadrature            |
           |==================================|
    sig -->|up                              a |--> pin
    sig -->|down                            b |--> pin
           +----------------------------------+


Module details
**************

.. automodule:: hmmc.output.stepdir
   :members:


Push-Pull
---------
Multiple isolated supplies are often required in high voltage Motor Control applications.

Alternatively to ready-made isolated DC/DC converters, a discrete, low power push-pull converter can be made using 2 MOSFETs, a COTS push-pull transformer and two diodes. This can be useful to reduce losses, optimize BOM or if space is constrained.

In the lowest power form, high-current FPGA IOs can be used to drive the transformer directly, in which case a full-bridge design is more desirable. Using standard Ethernet transformer, it's possible to transmit up tp 10mW of power per transformer from a 3.3V input.

If higher output voltages are desirable, inductor L can be added to form an isolated boost converter.
Then, set duty_cycle > perdiod so that the output voltage is boosted. Ethernet transformers were tested to produce >10V at over 50mW output from a 5V input, at 500kHz.

.. svgbob::
   :align: center

              .------∿∿ -._    _.-->|---------.
              |      *     )!!(     .--->|----+
           ||-+            )!!(    |          |
    ph_l --|+<-  V+ -∿∿ -._)!!(_.--+---+--||--+--Viso
           ||-+      L     )!!(    |   |  C
             _|_           )!!(    |  _|_
             GND   .-∿∿ -._)!!(____| GNDi
                   | *           
                ||-+
         ph_h --|+<-
                ||-+
                  _|_
                  GND

              _____
                   |
              F    +-∿∿ -._    _.-->|---------.
              P    | *     )!!(     .--->|----+
              G    |       )!!(    |          |
              A    +-----._)!!(_.--+---+--||--+--Viso
              _____|       )!!(    |   |  C
                           )!!(    |  _|_
                    -∿∿ -._)!!(____| GNDi
                     *

.. svgbob::
   :align: center

           +------------------------------------+   +----------------------+
           |            SoftStart               |   |       PushPull       |
           |====================================|   |======================|
    sig -->|duty_cycle_setpoint    cycle_update |<--|cycle_update    out_l |--> pin
    sig <--|done              duty_cycle_output |-->|duty_cycle      out_h |--> pin
           +------------------------------------+   +----------------------+


Module details
**************

.. automodule:: hmmc.output.pushpull
   :members:
