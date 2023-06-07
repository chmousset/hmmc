Math Modules
============

Fixed Point
-----------

`Fixed point arithmetic <https://en.wikipedia.org/wiki/Fixed-point_arithmetic>`_ is often used in signal processing or control applications as it allows a large ressource or power usage reduction versus floating point arithmetic. It is particularly suited for use with FPGA as they often integrate fixed point DSP blocks.

HMMC provide limited support for Fixed point signal through :class:`.FixedPointSignal`. Currently, only the **0.n** format is supported, which can represent a range of [-1; 1-2^-n/2].

.. csv-table:: 0.4 binary representation
	:header: "Real value", "Binary value"

	-1.000,0b1000
	-0.875,0b1001
	-0.125,0b1111
	0.000,0b0000
	0.125,0b0001
	0.750,0b0110
	0.875,0b0111


Usage
*****
:class:`.FixedPointSignal` inherits from :class:`migen.fhdl.structure.Signal` and is interoperable with them.

The main advantage is that is can easily connect fixed point signals of different resolution, extending or dropping bits as required. The MSB are connected together while the LSB are dropped/set to 0 if reducing/extending resolution.

.. csv-table:: extending and compressing resolution
	:header: "Real value", "0.4 representation", "0.6 extension", "0.3 representation", "0.3 real value"

	-1.000,0b1000,0b100000,0b100,-1.000
	-0.875,0b1001,0b100100,0b100,-1.000
	-0.125,0b1111,0b111100,0b111,-0.250
	0.000,0b0000,0b000000,0b000,0.000
	0.125,0b0001,0b000100,0b000,0.000
	0.750,0b0110,0b011000,0b011,0.75
	0.875,0b0111,0b011100,0b011,0.75


.. note::

	:meth:`.FixedPointSignal.eq` will handle resolution extension and compression even if the target is of type :class:`migen.fhdl.structure.Signal` ; however :meth:`migen.fhdl.structure.Signal.eq` will not do the same and you will have to adapt the resolution manually when connecting back to :class:`migen.fhdl.structure.Signal`:

	.. code:: python

		from migen import Signal
		from hmmc.math.fixed import FixedPointSignal

		inp = Signal(6)
		fixed = FixedPointSignal(7)
		out = Signal(5)
		self.comb += [
			fixed.eq(inp),  # this will extend 'inp' resolution to 0.7
			# out.eq(fixed),  <-- this won't respect the 0.5 fixed point representation
			FixedPointSignal.eq(out, fixed),  # this will lower 'fixed' resolution to 0.5
		]

Module Details
**************

.. automodule:: hmmc.math.fixedpoint
	:members:
