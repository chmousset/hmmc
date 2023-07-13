import unittest
import inspect
from migen.fhdl.verilog import convert
from migen import Module, Signal, run_simulation
from hmmc.math.dsp import add_signed_detect_overflow, MulFixedPoint
from hmmc.math.fixedpoint import FloatFixedConverter, FixedPointSignal
from hmmc.utils.verilator import ModuleVerilog, VerilatorBuilder


class add_signed_detect_overflow_dut(Module):
    def __init__(self):
        self.A = A = Signal((8, True))
        self.B = B = Signal((8, True))
        self.submodules.add = add_signed_detect_overflow(A, B)
        self.C = self.add.C
        self.overflow = self.add.overflow
        self.underflow = self.add.underflow


class TestMathDspAddSignedDetectOverflow(unittest.TestCase):
    def add_signed_detect_overflow_test(self, dut):
        yield
        values = [10, -10, -120, 120]
        for a in values:
            for b in values:
                c = a + b
                overflown = c
                if c > 127:
                    overflown = c - 256
                if c < -128:
                    overflown = c + 256
                yield dut.A.eq(a)
                yield dut.B.eq(b)
                yield
                dut_c = (yield dut.C)
                self.assertEqual(dut_c, overflown)
                self.assertEqual((yield dut.overflow), (1 if c > overflown else 0))
                self.assertEqual((yield dut.underflow), (1 if c < overflown else 0))
        yield

    def test_math_dsp_add_signed_detect_overflow(self):
        dut = add_signed_detect_overflow_dut()
        run_simulation(dut, [self.add_signed_detect_overflow_test(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")


class TestMathDspMul(unittest.TestCase):
    def mul_test(self, dut, a, b):
        yield dut.A.eq(a)
        yield dut.B.eq(b)
        yield
        yield
        self.assertEqual((yield dut.C), a * b)

    def fp_mul_test(self, dut, a, b, c_min, c_max):
        yield dut.A.eq(a)
        yield dut.B.eq(b)
        yield
        yield
        c = (yield dut.C)
        if c < 0:
            c = (c + (1 << dut.C.nbits)) % (1 << dut.C.nbits)
        print(f"{a}, {b}, {c_min}, {c_max}, {c}")
        self.assertGreaterEqual(c, c_min)
        self.assertGreaterEqual(c_max, c)

    def test_math_dsp_mul_u(self):
        dut = MulFixedPoint(8, 8)
        self.assertEqual(dut.C.nbits, 16)
        self.assertEqual(dut.C.radix_nbits, 16)
        self.assertEqual(dut.C.signed, False)

        def tb(dut):
            yield from self.mul_test(dut, 10, 20)
            yield from self.mul_test(dut, 0, 20)
            yield from self.mul_test(dut, 5, 0)

        run_simulation(dut, [tb(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_math_dsp_mul_s(self):
        fpc_in = FloatFixedConverter(8, 7, True, saturate=True)
        fpc_out = FloatFixedConverter(15, 14, True, saturate=True)
        dut = MulFixedPoint((8, True), (8, True))
        self.assertEqual(dut.C.nbits, 15)
        self.assertEqual(dut.C.radix_nbits, 14)
        self.assertEqual(dut.C.signed, True)

        values = [0.0, 0.9, 0.5]
        t_min = 0.99
        t_max = 1.01

        for v in values.copy():
            if v != 0.0:
                values += [-1 * v]

        def tb(dut):
            for a in values:
                for b in values:
                    _c_min = t_min * a * b
                    _c_max = t_max * a * b
                    c_min = min(_c_max, _c_min)
                    c_max = max(_c_max, _c_min)
                    yield from self.fp_mul_test(dut,
                        fpc_in.convert_float(a),
                        fpc_in.convert_float(b),
                        fpc_out.convert_float(c_min),
                        fpc_out.convert_float(c_max))

        run_simulation(dut, [tb(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_math_dsp_mul_v(self):
        dut = MulFixedPoint((8, True), (8, True))
        v = convert(dut, ios={dut.A, dut.B, dut.C})
        with open(inspect.stack()[0][3] + ".v", 'w') as f:
            f.write(str(v))

    def test_math_dsp_mul_verilator(self):
        buildpath = f"build/{inspect.stack()[0][3]}/"
        dut = MulFixedPoint((8, True), (8, True))
        dut.C_scaled = FixedPointSignal((10, True), 9)
        dut.comb += dut.C_scaled.eq(dut.C)
        dut.A.name_override = 'A'
        dut.B.name_override = 'B'
        dut.C.name_override = 'C'
        dut.C_scaled.name_override = 'C_scaled'
        dut._ios = {dut.A, dut.B, dut.C, dut.C_scaled}
        ModuleVerilog.verilog(dut, f"{buildpath}top.v")

        A_value = -40
        B_value = 123
        C_value = A_value * B_value
        C_scaled_value = C_value // 32

        builder = VerilatorBuilder(buildpath)
        builder.add_source("tb.cpp", builder.format_builtin_template(
            includes="#include <cassert>",
            defines=f"#define VM_TRACE_FILE \"build/{inspect.stack()[0][3]}/trace.vcd\"",
            main_code="\n    ".join(["    // main testbench",
                        "clock_tick(contextp, top);",
                        f"top->A = {A_value};",
                        f"top->B = {B_value};",
                        "clock_tick(contextp, top);",
                        f'assert(top->C == ((unsigned int){C_value} & 0x7FFF));'
                        f'assert(top->C_scaled == ((unsigned int){C_scaled_value} & 0x3FF));'
                        ]),
            return_code="    return 0;"))
        builder.add_source("top.v")
        builder.cmake("test_utils_verilator", True)
