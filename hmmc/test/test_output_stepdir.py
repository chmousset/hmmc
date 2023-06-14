import unittest
import inspect
from random import randint
from migen import Module, Signal, passive, run_simulation
from hmmc.output.stepdir import StepDir, Quadrature


class TestOutputStepDir(unittest.TestCase):
    @passive
    def count_pos(self, dut):
        self.pos = 0
        while True:
            if (yield dut.step):
                if (yield dut.dir):
                    self.pos += 1
                else:
                    self.pos -= 1
                while (yield dut.step):  # wait for end of pulse
                    yield
            else:
                yield

    def up(self, dut, pause):
        yield dut.up.eq(1)
        yield dut.down.eq(0)
        yield
        yield dut.up.eq(0)
        for _ in range(pause):
            yield

    def down(self, dut, pause):
        yield dut.up.eq(0)
        yield dut.down.eq(1)
        yield
        yield dut.down.eq(0)
        for _ in range(pause):
            yield

    def invalid(self, dut, pause):
        yield dut.up.eq(1)
        yield dut.down.eq(1)
        yield
        yield dut.down.eq(0)
        yield dut.up.eq(0)
        for _ in range(pause):
            yield

    def updown(self, dut):
        yield

        yield from self.up(dut, 50)
        yield from self.up(dut, 50)
        yield from self.up(dut, 50)
        yield from self.down(dut, 50)
        yield from self.down(dut, 50)
        yield from self.down(dut, 50)
        yield from self.up(dut, 50)
        yield from self.down(dut, 50)

    def pulse_rand_pause(self, dut, value):
        pause = randint(0, 20)
        if value == 0:
            yield from self.invalid(dut, pause)
        elif value == 1:
            yield from self.up(dut, pause)
        elif value == -1:
            yield from self.down(dut, pause)

    def updown_fast(self, dut):
        yield

        yield from self.up(dut, 10)
        yield from self.down(dut, 5)
        yield from self.up(dut, 1)
        yield from self.down(dut, 0)
        yield from self.invalid(dut, 0)
        yield from self.down(dut, 0)
        yield from self.up(dut, 0)
        yield from self.up(dut, 10)
        yield from self.down(dut, 50)
        # result should be 0

    def updown_sequence(self, dut, sequence):
        for value in sequence:
            yield from self.pulse_rand_pause(dut, value)
        for _ in range(40):
            yield

    def test_output_stepdir_stepdir(self):
        dut = StepDir(5, 10)
        run_simulation(dut, [self.updown(dut),
                            self.count_pos(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_output_stepdir_rand(self):
        for i in range(10):
            seq = [randint(-1, 1) for _ in range(4)]
            print(f"test rand sequence #{i}: {seq}")
            dut = StepDir(5, 10)
            run_simulation(dut, [self.updown_sequence(dut, seq),
                                self.count_pos(dut)],
                vcd_name=inspect.stack()[0][3] + f"{i}.vcd")
            assert self.pos == sum(seq)
