from enum import Enum, IntEnum

class RaritanSensorState(Enum):
    """"""

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
