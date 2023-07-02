
import enum


class KeyStatus(str, enum.Enum):
    works = "works"
    broken = "broken"
    unknown = "unknown"
