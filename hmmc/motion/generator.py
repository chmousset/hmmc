from migen import Module, Signal, If, Cat, C, Replicate
from hmmc.math.dsp import add_signed_detect_overflow


def move_cmd_layout(w_position, w_speed, w_acceleration):
    return [
        ("target_position", (w_position, True)),
        ("start_speed", (w_speed, True)),
        ("acceleration", (w_acceleration, True))]


class MotionGeneratorAxis(Module):
    """This module generates position and speed setpoints in realtime.

    :param w_position: size of the position accumulator
    :type w_position: int
    :param w_speed: size of the speed accumulator
    :type w_speed: int
    :param w_acceleration: size of the acceleration state
    :type w_acceleration: int

    :inputs:
        - **cmd_valid** (*Signal()*) - set to '1' when other cmd_* signals are valid
        - **cmd_start_speed** (*Signal(w_speed)*) - internal state 'speed' set to this value when
          cmd_valid & cmd_ready
        - **cmd_target_position** (*Signal(w_position)*) - position to reach (and stop to)
        - **cmd_acceleration** (*Signal(w_acceleration)*) - internal state 'acceleration' set to
          this value when cmd_valid & cmd_ready
        - **flush** (*Signal()*) - when '1', set speed to 0 and target to actual position

    :outputs:
        - **cmd_ready** (*Signal()*) - '1' when 'position' == previous 'cmd_target_position'
        - **acceleration** (*Signal(w_acceleration)*) - current acceleration
        - **position** (*Signal((w_position, True))*) - internal state
        - **speed_raw** (*Signal((w_speed + w_acceleration, True))*) - internal state
        - **speed** (*Signal(w_speed)*) - internal state
        - **down** (*Signal()*) - if '1', position decreased in this clock cycle
        - **up** (*Signal()*) - if '1', position increased in this clock cycle
        - **done** (*Signal()*) - 'cmd_target_position' is reached
    """

    def __init__(self, w_position=20, w_speed=20, w_acceleration=20):
        assert w_acceleration <= w_speed  # can't saturate speed in one cycle

        # inputs
        self.cmd_valid = Signal(name="cmd_valid")
        self.cmd_start_speed = Signal(w_speed, name="cmd_start_speed")
        self.cmd_target_position = Signal(w_position, name="cmd_target_position")
        self.cmd_acceleration = Signal(w_acceleration, name="cmd_acceleration")
        self.flush = Signal(name="flush")

        # input buffer
        self.acceleration = acceleration = Signal((w_acceleration, True))

        # internal state
        target_position = Signal((w_position, True))
        cnt = Signal((w_speed, True))  # "substep" counter. Generate a step when it over/underflows
        position = Signal((w_position, True))
        speed_raw = Signal((w_speed + w_acceleration, True))
        speed = Signal(w_speed)
        self.submodules.addsat = add_signed_detect_overflow(cnt, speed)

        # outputs
        self.cmd_ready = Signal(name="cmd_ready")
        self.position = position
        self.speed_raw = speed_raw
        self.speed = speed
        self.down = Signal(name="down")
        self.up = Signal(name="up")
        self.done = Signal(name="done")

        self.sync += [
            If(self.flush,
                target_position.eq(position),
                speed_raw.eq(0),
            ).Elif(~self.done,
                cnt.eq(self.addsat.C),
                If(((speed == 1) & acceleration[-1]) | ((speed == Replicate(C(1), w_speed))
                    & ~acceleration[-1]),
                    # make sure speed does not change sign on deceleration
                    speed_raw.eq(speed_raw),
                ).Else(
                    # sign extend acceleration before adding it to speed
                    speed_raw.eq(speed_raw + acceleration),
                    # speed_raw.eq(speed_raw +
                    #     Cat(acceleration, Replicate(acceleration[-1], w_speed))),
                )
            ).Elif(self.cmd_valid,  # load next motion command
                speed_raw.eq(Cat(Replicate(self.cmd_start_speed[-1], w_acceleration),
                                 self.cmd_start_speed)),
                target_position.eq(self.cmd_target_position),
                acceleration.eq(self.cmd_acceleration),
            ),
            If(self.addsat.overflow,
                position.eq(position + 1),
            ).Elif(self.addsat.underflow,
                position.eq(position - 1),
            )
        ]

        self.comb += [
            self.up.eq(self.addsat.overflow),
            self.down.eq(self.addsat.underflow),
            speed.eq(speed_raw[-w_speed:]),
            self.done.eq(position == target_position),
            self.cmd_ready.eq(self.done),
        ]

    def perf_limits(self, fclk, resolution):
        """Give resolution and maximum for speed and acceleration"""
        speed_res = 1 / 2**self.w_speed * resolution * fclk
        speed_max = resolution * fclk
        accel_res = 1 / 2**(self.w_speed + self.w_acceleration) * resolution * fclk**2
        accel_max = accel_res * 2**self.w_acceleration

        return speed_res, speed_max, accel_res, accel_max
