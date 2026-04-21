"""
_dummy_gps.py
16.04.2026

imitates gpsd library with cached data

Author:
Nilusink
"""

from dataclasses import dataclass


FILE: str = "./gps_buff.csv"


@dataclass(frozen=True)
class GPSDataLine:
    """one line of gps data"""
    mode: int
    lat: float = 0
    lon: float = 0
    speed: float | None = 0
    angle: float | None = 0


class GPSResponse:
    """dummy"""

    def __init__(self, line: GPSDataLine) -> None:
        self.mode = line.mode
        self.lat = line.lat
        self.lon = line.lon
        self._speed: float = line.speed / 3.6 if line.speed else 0

    def speed(self) -> float:
        """dummy"""
        return self._speed


class GPSD:
    """gpsd dummy"""

    def __init__(self) -> None:
        with open(FILE, "r") as f:
            raw_data = f.readlines()[:-1]

        self.__i = 0
        self.data: list[GPSDataLine] = []
        for line in raw_data:
            mode, lat, lon, speed, angle = line.split(",")
            try:
                s = float(speed)
                a = float(angle)
                self.data.append(
                    GPSDataLine(
                        int(mode), float(lat), float(lon),
                        s if s > .1 else None, a if a != 0 else None
                    )
                )

            except ValueError:
                self.data.append(GPSDataLine(mode=0, speed=None, angle=None))

    def connect(self) -> None:
        """dummy"""

    def get_current(self) -> GPSResponse:
        """return a gps response object"""
        res = GPSResponse(self.data[self.__i])
        self.__i += 1

        return res


gpsd = GPSD()
