import unittest
import inspect
from migen import run_simulation, passive
from hmmc.motion.generator import MotionGeneratorAxis


class TestMotionGeneratorAxis(unittest.TestCase):
    def wait_done(self, dut, timeout):
        while (yield dut.done) == 0:
            assert timeout
            timeout -= 1
            yield

    def wait_ready(self, dut, timeout):
        while (yield dut.cmd_ready) == 0:
            assert timeout
            timeout -= 1
            yield

    def push_cmd(self, dut, target_position, start_speed, acceleration, timeout):
        yield
        yield dut.cmd_acceleration.eq(acceleration)
        yield dut.cmd_start_speed.eq(start_speed)
        yield dut.cmd_target_position.eq(target_position)
        yield dut.cmd_valid.eq(1)
        yield
        yield dut.cmd_valid.eq(0)
        yield
        yield from self.wait_done(dut, timeout)

    def push_cmds(self, dut):
        acc = 2**19 - 1

        yield from self.push_cmd(dut, 8, 1000, acc, 7000)
        assert 8 == (yield dut.position)
        yield from self.push_cmd(dut, 16, (yield dut.speed), -1 * acc, 7000)
        assert 16 == (yield dut.position)
        yield from self.push_cmd(dut, 8, -1000, -1 * acc, 7000)
        assert 8 == (yield dut.position)
        yield from self.push_cmd(dut, 0, (yield dut.speed) - 10, acc, 7000)
        assert 0 == (yield dut.position)

    @passive
    def check_pos_at_done(self, dut, sequence):
        while (yield dut.done):  # wait for the generator to run its first command
            yield
        for pos in sequence:  # check all positions in sequence are met
            print(f"{inspect.stack()[0][3]}: Sequence [{pos}]")
            while (yield dut.done) == 0:
                yield
            assert (yield dut.position) == pos
            assert pos == len(self.up_pulses) - len(self.down_pulses)
            while (yield dut.done):  # wait for the generator to run the next command
                yield
        while True:  # check there are no other motion afterwards
            assert (yield dut.done)
            yield

    @passive
    def extract_pulses(self, dut):
        self.up_pulses = []
        self.down_pulses = []
        cnt = 0
        while True:
            if (yield dut.up):
                self.up_pulses += [cnt]
            if (yield dut.down):
                self.down_pulses += [cnt]
            cnt += 1
            yield

    def test_motiongenerator_commands(self):

        dut = MotionGeneratorAxis()
        run_simulation(dut, [self.push_cmds(dut),
                             self.check_pos_at_done(dut, [8, 16, 8, 0]),
                             self.extract_pulses(dut)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
