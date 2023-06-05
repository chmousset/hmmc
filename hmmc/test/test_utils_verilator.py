import unittest
from hmmc.utils.verilator import ModuleVerilog, VerilatorBuilder, copy_package_file
from migen import Signal


class Adder(ModuleVerilog):
    def __init__(self):
        self.a = Signal(32, name="a")
        self.b = Signal(32, name="b")
        self.c = Signal(32, name="c")
        self.sync += self.c.eq(self.a + self.b)
        self._ios = {self.a, self.b, self.c}


class TestUtilsVerilator(unittest.TestCase):
    def test_verilator(self):
        buildpath = "build/test_utils_verilator/"
        dut = Adder()
        dut.verilog(f"{buildpath}top.v")

        builder = VerilatorBuilder(buildpath)
        copy_package_file("hmmc.data.cpp", "adder.cpp", buildpath + "tb.cpp")
        builder.add_source("tb.cpp")
        builder.add_source("top.v")
        builder.cmake("test_regulator_hyst_threep", True)
