import unittest
import inspect
from hmmc.input.mitsubishi import ECNMEncoder
from migen import run_simulation, passive


class TestMitsubishi(unittest.TestCase):
    @passive
    def encoder(self, dut, cmd_response):
        yield dut.tx_idle.eq(1)
        while True:
            if (yield dut.tx_valid):
                cmd = (yield dut.tx)
                yield dut.tx_idle.eq(0)
                for _ in range(10):
                    yield  # simulate transmission
                yield dut.tx_idle.eq(1)
                for resp_byte in cmd_response.get(cmd, []):
                    yield dut.rx.eq(resp_byte)
                    yield dut.rx_valid.eq(1)
                    yield
                    while (yield dut.rx_ready) == 0:
                        yield
                yield dut.rx_valid.eq(0)
            else:
                yield

    def encoder_ok_check(self, dut, value, timeout_cnt):
        timeout = True
        for _ in range(timeout_cnt):
            self.assertEqual((yield dut.cs_error), 0)
            if (yield dut.position_valid):
                self.assertEqual((yield dut.position), value)
                yield
                self.assertEqual((yield dut.idle), 1)
                timeout = False
                break
            yield
        self.assertEqual(timeout, False, msg="Timedout waiting for position_valid")

    def encoder_cs_error_check(self, dut, timeout_cnt):
        timeout = True
        for _ in range(timeout_cnt):
            self.assertEqual((yield dut.position_valid), 0)
            if (yield dut.cs_error):
                yield
                self.assertEqual((yield dut.idle), 1)
                timeout = False
                break
            yield
        self.assertEqual(timeout, False, msg="Timedout waiting for cs_error")

    def encoder_timeout(self, dut, timeout_cnt):
        for _ in range(timeout_cnt):
            self.assertEqual((yield dut.position_valid), 0)
            self.assertEqual((yield dut.cs_error), 0)

    def add_cs(self, response, bogous_cs=False):
        cs = 0
        print(response)
        for byte_value in response:
            cs = cs ^ byte_value
        return response + [cs + (1 if bogous_cs else 0)]

    def test_input_mitsubishi_ok(self):
        fclk = 5e6
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x32: self.add_cs([0x32, 0xde, 0xad, 0xbe, 0xef])}
        run_simulation(dut, [
            self.encoder(dut, cmd_response),
            self.encoder_ok_check(dut, 0xefbead, int(fclk / dut.baudrate) * 40)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_cs_error(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x32: self.add_cs([0x32, 0, 0xde, 0xad, 0xbe, 0xef], True)}
        run_simulation(dut, [
            self.encoder(dut, cmd_response),
            self.encoder_cs_error_check(dut, int(fclk / dut.baudrate) * 40)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_missing_byte(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x32: [0x32, 0, 0xde, 0xad, 0xbe, 0xef]}  # missing a byte
        run_simulation(dut, [
            self.encoder(dut, cmd_response),
            self.encoder_timeout(dut, int(fclk / dut.baudrate) * 40)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_timeout(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x02: [0x01]}  # won't answer to command 0x32
        run_simulation(dut, [
            self.encoder(dut, cmd_response),
            self.encoder_timeout(dut, int(fclk / dut.baudrate) * 40)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
