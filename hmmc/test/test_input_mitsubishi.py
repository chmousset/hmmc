import unittest
import inspect
from hmmc.input.mitsubishi import ECNMEncoder
from migen import run_simulation, passive


class TestMitsubishi(unittest.TestCase):
    known_good_frame = [0x32, 0x21, 0x80, 0xC8, 0x46, 0x71, 0xCC, 0x80, 0x20]

    @passive
    def encoder(self, dut, fclk, cmd_response):
        periods_tx = int(fclk / 2.5e6 * 10) + 1
        yield dut.tx_idle.eq(1)
        while True:
            if (yield dut.tx_valid):
                cmd = (yield dut.tx)
                yield dut.tx_idle.eq(0)
                for _ in range(periods_tx):
                    yield  # simulate transmission
                yield dut.tx_idle.eq(1)
                yield
                for resp_byte in cmd_response.get(cmd, []):
                    for _ in range(periods_tx):
                        yield  # simulate reception
                    yield dut.rx.eq(resp_byte)
                    yield dut.rx_valid.eq(1)
                    yield
                    while (yield dut.rx_ready) == 0:
                        yield
                    yield dut.rx_valid.eq(0)
            else:
                yield

    def encoder_ok_check(self, dut, value, timeout_cnt):
        got_valid_pos = False
        while timeout_cnt:
            self.assertEqual((yield dut.cs_error), 0)
            if (yield dut.position_valid):
                self.assertEqual((yield dut.position), value)
                yield
                while (yield dut.idle) == 0:
                    yield
                    self.assertGreaterEqual(timeout_cnt, 0, msg="Timeout waiting for idle after position_valid")
                    timeout_cnt -= 1
                got_valid_pos = True
                break
            yield
            self.assertGreaterEqual(timeout_cnt, 0)
            timeout_cnt -= 1
        self.assertEqual(got_valid_pos, True, msg="Timeout waiting for position_valid")

    def encoder_cs_error_check(self, dut, timeout_cnt):
        got_cs_err = False
        while timeout_cnt:
            if (yield dut.cs_error):
                yield
                while (yield dut.idle) == 0:
                    yield
                    self.assertEqual((yield dut.cs_error), 0)
                    self.assertGreaterEqual(timeout_cnt, 0, msg="Timeout waiting for idle after cs_error")
                    timeout_cnt -= 1
                got_cs_err = True
                break
            yield
            self.assertGreaterEqual(timeout_cnt, 0)
            timeout_cnt -= 1
        self.assertEqual(got_cs_err, True, msg="Timeout waiting for cs_error")

    def encoder_timeout(self, dut, timeout_cnt):
        assert timeout_cnt > 1
        for _ in range(timeout_cnt):
            self.assertEqual((yield dut.position_valid), 0)
            yield

    def assert_critical_error(self, dut, timeout_cnt):
        self.assertEqual((yield dut.critical_error), 0)
        for _ in range(timeout_cnt):
            yield
        self.assertEqual((yield dut.critical_error), 1)

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
        self.assertEqual(self.known_good_frame, self.add_cs(self.known_good_frame[:-1]))
        cmd_response = {0x32: self.known_good_frame}
        timeout = int(fclk / dut.baudrate) * 10 * (9 + 5)
        run_simulation(dut, [
            self.encoder(dut, fclk, cmd_response),
            self.encoder_ok_check(dut, 0x46C880, timeout)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_cs_error(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x32: self.add_cs(self.known_good_frame[:-1], True)}
        timeout = int(fclk / dut.baudrate) * 10 * (9 + 5)
        run_simulation(dut, [
            self.encoder(dut, fclk, cmd_response),
            self.encoder_cs_error_check(dut, timeout)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_missing_byte(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x32: self.known_good_frame[:-1]}  # missing a byte
        timeout = int(fclk / dut.baudrate) * 10 * (8 + 5)
        run_simulation(dut, [
            self.encoder(dut, fclk, cmd_response),
            self.encoder_timeout(dut, timeout)],
            vcd_name=inspect.stack()[0][3] + ".vcd")

    def test_input_mitsubishi_timeout(self):
        fclk = 5000_000
        dut = ECNMEncoder(fclk)
        dut.idle = dut.fsm.ongoing("IDLE")
        cmd_response = {0x02: [0x01]}  # won't answer to command 0x32
        timeout = int(fclk / dut.baudrate) * 10 * 10
        run_simulation(dut, [
            self.encoder(dut, fclk, cmd_response),
            self.encoder_timeout(dut, timeout),
            self.assert_critical_error(dut, timeout)],
            vcd_name=inspect.stack()[0][3] + ".vcd")
