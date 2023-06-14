Motion Modules
==============

MotionGeneratorAxis
-------------------

Generate (position, speed) values for a single Axis based on three parameters:

  - `start_speed`
  - `target_position`
  - `acceleration`

It can be synchronized with other Motion Generators, and can also generate (up, down) pulses for driving step/dir or quadrature drivers.

As it's entirely based on integer addition so it is speed and resources efficient.

Usage
*****

Resolution calculation
~~~~~~~~~~~~~~~~~~~~~~

First, you must know the size of a single position increment, and the maximum travel range. Usually, this is equal to an encoder resolution or a stepper microstep resolution and the size of the machine.

`w_position` should be *at least* log2(travel / position_resolution) + 1 to cover the whole travel of the machine to control.
`w_speed` and `w_acceleration` will determine the maximum acceleration and maximum speed that can be reached, which can be calculated using :meth:`.hmmc.motion.MotionGeneratorAxis.perf_limits`
Here is a calculation example:

.. code-block:: python

    fclk = 50E6  # system clock 50MHz
    travel = 1  # 1 meter
    pitch = 5e-3  # 5mm pitch ballscrew
    cpr = 1600  # 400 lines = 1600 Count Per Revolution encoder
    resolution = pitch / cpr
    w_position = ceil(log2(travel / resolution)) + 1  # 20

    generator = MotionGeneratorAxis(...)
    speed_res, speed_max, accel_res, accel_max = generator.perf_limits(fclk, resolution)


Synchronization
~~~~~~~~~~~~~~~

Multiple Motion Generators can be synchronized using the `cmd_ready` and `cmd_valid` signals. A logic `AND` of multiple `cmd_ready` signals will be True only when all Motion Generators have reached the `target_position`.

.. note::

    Care must be given when synchronizing multiple Motion Generators. The parameters of the commands of all Motion Generators must be chosen in such a way that all Motion Generators finish their movement around the same time.
    Synchronizing multiple Motion Generators that way require to delay the fastest MP between commands, 'stopping' the Axis for short periods of time and introducing jittern in the movement speed of the slowest generators.

Using the outputs
~~~~~~~~~~~~~~~~~

`.position` setpoint can be fed to a motor position control loop (ex: PID+FOC), or readback in order to be displayed. It's valid ever clock tick.

`.speed` is an internal state of the Generator that it can be used as a feed-forward for a position regulator.

`.done` is '1' when the `.position` == `target_position`

`.up`, `.down` are incremental outputs of `.position`, useful to control STEP/DIR or quadrature drives. Valid for each clock cycle, so it usually have to be extended before being fed to a driver.

Module Details
**************

.. automodule:: hmmc.motion.generator
    :members:
