from enum import Enum, IntEnum

class RaritanSensorState(Enum):
    """"""

    def friendly_name(self) -> str:
        return self.name.title()


    @classmethod
    def options(cls) -> list[str]:
        return [opt.friendly_name() for opt in list(cls)]

class OnOff(RaritanSensorState, IntEnum):
    """"""

    OFF = 0
    ON = 1

class OpenClosed(RaritanSensorState, IntEnum):
    """"""

    OPEN = 0
    CLOSED = 1

class NormalAlarmed(RaritanSensorState, IntEnum):
    """"""

    NORMAL = 0
    ALARMED = 1


class OkFaulted(RaritanSensorState, IntEnum):
    """"""

    OK = 0
    FAULT = 1


class ResidualCurrentStatus(RaritanSensorState, IntEnum):
    """"""

    NORMAL = 0
    WARNING = 1
    CRITICAL = 2
    SELF_TEST = 3
    FAILURE = 4
