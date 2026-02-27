import dataclasses
import json


@dataclasses.dataclass
class Stats:
    Winrate: float

#dumps @dataclass into Json string
#json.dumps(asdict(p1))