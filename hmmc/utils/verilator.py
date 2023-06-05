"""
Verilator bindings
==================

Verilator is a high performance Verilog to cpp simulator converter.
This wrapper simplifies building a simulator from a Migen HDL and a CPP testbench.
"""

import os
from datetime import datetime
from pathlib import Path
import subprocess

from migen import Module, Record
from migen.fhdl.verilog import convert
from migen.fhdl.specials import Special
from os import makedirs


class ModuleVerilog(Module):
    """Migen Module easy to convert to Verilog"""
    def verilog(self, filename):
        """Convert the Module to Verilog and write it on disk.

        The Module must have either a self._ios set() containing all IO Signal() and Record(), or a
        self.get_ios() function that return the same.

        This function automatically flattens the Record() IOs to make it compatible with Verilog.
        """
        if hasattr(self, "get_ios"):
            ios = self.get_ios()
        else:
            ios = self._ios
        # flatten records to be usable as ios
        ios = {io.iter_flat() if isinstance(io, Record) else io for io in ios}
        # Make subdirs
        filepath = Path(filename)
        dirpath = filepath.parent.absolute()
        if not dirpath.exists():
            makedirs(dirpath)
        # assert filepath.is_file()
        # convert
        v = convert(self, ios=ios)
        with open(filename, 'w') as f:
            f.write(str(v))


# Migen to Verilog conversion
class RawVerilog(Special):
    """Allows to inject raw Verilog.

    :param verilog: raw verilog to inject
    :type verilog: str
    """
    def __init__(self, verilog: str):
        Special.__init__(self)
        self._verilog = verilog

    def emit_verilog(raw_verilog, ns, add_data_file):
        return raw_verilog._verilog


class VerilatorVcdDirective(RawVerilog):
    """Insert a $dumpfile() valid under Verilator

    This is an easy alternative to using a VerilatedVcdC object. It requires '--trace' to be passed
    when building (CMake) the testbench, and to pass the '+trace' argument when running the
    testbench executable.
    """
    def __init__(self, path):
        super().__init__(
            "initial begin\n"
            + "  if ($test$plusargs(\"trace\") != 0) begin\n"
            + f"     $display(\"[%0t] Tracing to {path}\\n\", $time);\n"
            + f"     $dumpfile(\"{path}\");\n"
            + "     $dumpvars();\n"
            + "  end\n"
            + "  $display(\"[%0t] Model running...\\n\", $time);\n"
            + "end\n")


class VerilatorBuilder:
    """Verilator Testbench builder.

    It simplifies the call to CMake to build the testbench, and allows Verilator to be part of the
    unit tests.

    :param build_path: directory in which sources will be copied and CMake will be called
    :type build_path: str or Path object
    """
    def __init__(self, build_path):
        self.sources = {
            ".v": [],
            ".cpp": [],
        }
        self.build_path = Path(build_path)

    def add_source(self, path):
        """Add source file to be built.
        Currently .cpp and .v files are recognized.

        :param path: either a path to a source file or a list of files
        :type path: str, Path, list(str) or list(Path)
        """
        if isinstance(path, list):
            for p in path:
                self.add_source(self, p)
        else:
            extension = os.path.splitext(path)[1]
            if extension not in self.sources:
                raise ValueError(f"file {path} not of supported type {self.sources.keys()}")
            self.sources[extension] += [str(path)]

    def cmake(self, exec_name, call=False):
        """Generate CMakeLists.txt and call CMake

        Once this function has been called, the testbench executable will be present in the build
        directory. It raises an exception if it could not build the testbench executable.
        The testbench won't be run.

        :param exec_name: testbench executable name
        :type exec_name: str or Path
        """
        # Make sure the build path exists
        buildpath = self.build_path.joinpath('build')
        if not os.path.isdir(buildpath):
            os.makedirs(buildpath)

        # generate CMakeLists.txt
        v_sources = " ".join(self.sources[".v"])
        cpp_sources = " ".join(self.sources[".cpp"])
        include_dirs = " ".join([*set(str(Path(source).parent) for source in self.sources[".v"])])
        with open(os.path.join(self.build_path, "CMakeLists.txt"), 'w') as f:
            f.write(f"# Generated on {datetime.now()}\n"
                    "cmake_minimum_required(VERSION 3.8)\n"
                    f"project({exec_name})\n"
                    "set(CMAKE_CXX_FLAGS \"${CMAKE_CXX_FLAGS} -Os -std=gnu++17 -I ."
                    " -DPROGNAME=\\\\\\\"sim\\\\\\\"\")\n"
                    "find_package(verilator HINTS $ENV{VERILATOR_ROOT} ${VERILATOR_ROOT})\n"
                    "if (NOT verilator_FOUND)\n"
                    "  message(FATAL_ERROR \"Verilator was not found. Either install it, or set"
                    " the VERILATOR_ROOT environment variable\")\n"
                    "endif()\n"
                    f"add_executable({exec_name} {cpp_sources})\n"
                    f"verilate({exec_name}\n"
                    f"  INCLUDE_DIRS {include_dirs}\n"
                    "  VERILATOR_ARGS -Wno-fatal -Os -x-assign 0\n"
                    f"  SOURCES {v_sources})\n"
                    f"add_executable({exec_name}_trace {cpp_sources})\n"
                    f"verilate({exec_name}_trace\n"
                    f"  INCLUDE_DIRS {include_dirs}\n"
                    "  VERILATOR_ARGS -Wno-fatal -Os -x-assign 0 --trace\n"
                    f"  SOURCES {v_sources})\n")

        if call:
            current_path = os.getcwd()
            os.chdir(buildpath)
            if subprocess.Popen(["cmake", ".."]).wait() != 0:
                raise Exception("cmake failed")
            if subprocess.Popen(["make", "-j"]).wait() != 0:
                raise Exception("make failed")
            os.chdir(current_path)


def copy_package_file(package, resource_name, target):
    """Copies the source file from an installed package to target.

    Primarly used to access hmmc.data.cpp files, regardless of the specific installation mean of the
    package.

    :param package: module name. Ex: 'hmmc.data.cpp'
    :type package: str
    :param resource_name: file name. Ex: 'adder.cpp'
    :type resource_name: str
    :param target: path to copy the content to
    :type target: str or Path
    """ 
    from pkg_resources import resource_string as resource_bytes
    with open(target, 'w') as f:
        f.write(resource_bytes(package, resource_name).decode('utf-8'))
