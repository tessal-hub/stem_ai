from dataclasses import dataclass


@dataclass(frozen=True)
class PortDescription:
    index: int
    role: str
    name: str
    description: str


class ExerciseManager:
    INPUT_COUNT = 15
    OUTPUT_COUNT = 15

    def __init__(self) -> None:
        self._ports = self._build_default_ports()
        self._requirement = (
            "Mục tiêu: xây dựng app giao tiếp UART với STM32.\n"
            "- Đọc trạng thái 15 cổng input từ STM32.\n"
            "- Điều khiển 15 cổng output gửi xuống STM32.\n"
            "- Tổng cộng 30 cổng I/O hiển thị rõ ràng trên giao diện.\n\n"
            "Ghi chú: phần giao thức UART chi tiết đang để khung, sẽ bổ sung khi có format frame."
        )

    def _build_default_ports(self) -> list[PortDescription]:
        ports: list[PortDescription] = []
        for i in range(1, self.INPUT_COUNT + 1):
            ports.append(
                PortDescription(
                    index=i,
                    role="Input",
                    name=f"IN{i:02d}",
                    description=f"Cổng đọc trạng thái số {i} (placeholder).",
                )
            )

        for i in range(1, self.OUTPUT_COUNT + 1):
            ports.append(
                PortDescription(
                    index=self.INPUT_COUNT + i,
                    role="Output",
                    name=f"OUT{i:02d}",
                    description=f"Cổng điều khiển số {i} (placeholder).",
                )
            )
        return ports

    def get_ports(self) -> list[PortDescription]:
        return self._ports

    def get_requirement_text(self) -> str:
        return self._requirement
