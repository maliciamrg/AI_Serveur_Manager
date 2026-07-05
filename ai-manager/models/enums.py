from enum import StrEnum


class ServerState(StrEnum):
    OFF = "OFF"
    BOOTING = "BOOTING"
    READY = "READY"
    BUSY = "BUSY"
    IDLE = "IDLE"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

