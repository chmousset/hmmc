Regulator
=========

Hysteretic regulator
--------------------

The Hysteretic comparator regulator is a type of `Bang-Bang <https://en.wikipedia.org/wiki/Bang%E2%80%93bang_control>`_ regulator that can provide great performance for first-order systems, if the loopback delay isn't too large.

As such, it can find its use in motor current or voltage regulation, as demonstrated in test/test_regulator_hyst.py

Compared to other more complex regulators like the PID, the Hysteretic regulator can be very frugal in term of logic utilisation while providing some self-tuning capabilities.

However, this regulator outputs a white noise that can be hearable or cause bigger problems if not in check. Adapting the hysteresis value is crucial for proper operation.

Tuning
******
An hysteretic regulator is always oscillating around the setpoint. The time at which the output changes state depends on many factors:

- The larger the hysteresis, the longer the switching duration
- The slower the system responds to the control, the longer the duration
- increase in noise will usually shorten the transition delays

Because all these parameters can evolve from system to system, and even during operation, dynamically configuring the hysteresis can allow to keep switching frequency, frequency response and noise shape in check.

Usage
*****

A HystRegulatorBitSerial can use directly the output of a sigma delta modulator ADC, such as the AMC1303, and output a control signal to a power stage like a half bridge driver.

.. svgbob::
   :align: center

        ┌─────────┐      ┌────────┐         R
        │ HystReg │      │        │       sense     Phase
        │         │      │ MOSFET │_______┌───┐__________
        │   output├─────>| Bridge │     │ └───┘ │
        │         │      │        │     │       │
        │         │      └────────┘     │       │
    ───>|setpoint │                     │       │
        │         │      ┌────────┐     │       │
        │         │      │        ├─────┘       │
        │ feedback|<─────┤AMC1303 │             │
        │         │      │        ├─────────────┘
        └─────────┘      └────────┘


It is advised however to place a :class:`.PulseGuard` module between the regulator and the bridge input.
A DeadTime Module can also be used if the bridge requires complementary input signals.

To provide self-tuning, an external module can monitor when the regulator's output is too short or too long, and increase or decrease the hysteresis accordingly.

Module details
**************

.. automodule:: hmmc.regulator.hyst
   :members:
