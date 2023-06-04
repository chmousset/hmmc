# Hardware Motion and Motor Control Library
This package has building blocks related to Motor and Motion Control. When combining them, it's possible to create various systems from a simple Step/Dir motion planner to driver stepper motor controllers, up to a fully-fledged, high-performance multi-axis servomotor controller.
It uses [migen](https://github.com/m-labs/migen) to generate [Verilog](https://en.wikipedia.org/wiki/Verilog) that will typically be synthetized in an FPGA, possibly using [LiteX](github.com/enjoy-digital/litex) as the build system.

## Hardware vs Software Motor and Motion Control advantages
CPUs typically aren't very good at performing high-frequency (>1MHz), low-jitter tasks.
This is why SoC typically embedded Hardware peripherals such as PWM, ADC or quadrature counters to perform the most critical realtime tasks, lowering the realtime constraints on the CPU.
Unfortunately, the huge variety of CPUs, peripherals and specific hardware optimizations makes it very hard to design a scalable Motor and Motion Control system without sacrifying performance or writing a lot of platform-specific code.

Thanks to the the availability of modern FPGAs, and modern HDL, it's possible to create a better Motion and Motor Controller:
- performant: 50MHz+ hard realtime is easy to acheive in an FPGA.
- flexible: using standard logic, nearly any make/model of FPGA can be used without adaptation.
- scalable: a single motor controller can be put on a 5$ FPGA, and 10+ motor controllers can be put on a 30$ FPGA, without negative impact on performance.

# Installation
In order to run the tests, you must install [Verilator](https://verilator.org/guide/latest/install.html).

# Usage
## Generate a Verilog design
See the examples/verilog.py

## Generate an FPGA bitstream
see example/icestick.py
