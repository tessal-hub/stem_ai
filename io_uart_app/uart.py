from dataclasses import dataclass
from typing import Optional

import serial
from serial.tools import list_ports


class UartError(RuntimeError):
    pass


@dataclass(frozen=True)
class UARTConfig:
    port: str
    baudrate: int


class UartClient:
    def __init__(self) -> None:
        self._serial: Optional[serial.Serial] = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def available_ports(self) -> list[str]:
        return [p.device for p in list_ports.comports()]

    def connect(self, config: UARTConfig) -> None:
        if not config.port:
            raise UartError("Port rỗng.")

        if self.connected:
            self.disconnect()

        try:
            self._serial = serial.Serial(
                port=config.port,
                baudrate=config.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            )
        except serial.SerialException as exc:
            raise UartError(str(exc)) from exc

    def disconnect(self) -> None:
        if self._serial is None:
            return
        self._serial.close()
        self._serial = None

    def write(self, payload: bytes) -> int:
        if not self.connected or self._serial is None:
            raise UartError("Chưa kết nối UART.")
        return self._serial.write(payload)

    def read_available(self) -> bytes:
        if not self.connected or self._serial is None:
            raise UartError("Chưa kết nối UART.")
        waiting = self._serial.in_waiting
        if waiting <= 0:
            return b""
        return self._serial.read(waiting)
