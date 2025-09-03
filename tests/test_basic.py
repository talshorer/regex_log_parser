import dataclasses
import datetime
import re
from typing import List, Optional, Tuple

from regex_log_parser import LogParser, rule

DATA_BASIC = """
rule1 a b c
rule2 7
rule3 3
rule1 k d h
rule4
rule2 10
rule2 NOTNUM
rule1 t m x NOTPARTOFMATCH
rule3
""".lstrip().splitlines()


class ParserBasic(LogParser):
    def __init__(self) -> None:
        super().__init__()
        self.r1: List[Tuple[str, str, str]] = []
        self.r2: List[int] = []
        self.r3: List[Optional[int]] = []

    @rule("rule1 (?P<first>[a-z]+) (?P<second>[a-z]+) (?P<third>[a-z]+)")
    def rule1(self, m: re.Match) -> None:
        self.r1.append((m.group("first"), m.group("second"), m.group("third")))

    @rule("rule2 (?P<number>[0-9]+)")
    def rule2(self, m: re.Match) -> None:
        self.r2.append(int(m.group("number")))

    @rule("rule3 ?(?P<extra>[0-9]+)?")
    def rule3(self, m: re.Match) -> None:
        group = m.group("extra")
        if group is not None:
            extra = int(group)
        else:
            extra = None
        self.r3.append(extra)


def test_hits() -> None:
    p = ParserBasic()
    p.run(DATA_BASIC)
    assert p.hits == {
        "rule1": 3,
        "rule2": 2,
        "rule3": 2,
    }


def test_groups() -> None:
    p = ParserBasic()
    p.run(DATA_BASIC)
    assert p.r1 == [
        ("a", "b", "c"),
        ("k", "d", "h"),
        ("t", "m", "x"),
    ]
    assert p.r2 == [7, 10]
    assert p.r3 == [3, None]


def test_subclass() -> None:
    class Sub(ParserBasic):
        def __init__(self) -> None:
            super().__init__()
            self.r4 = 0

        @rule("rule4")
        def rule4(self, m: re.Match) -> None:
            self.r4 += 1

    p = Sub()
    p.run(DATA_BASIC)
    assert p.r2 == [7, 10]
    assert p.r4 == 1


DATA_WITH_BASE = """
2025-08-22T14:26:40.123456Z|INF|rule1
2025-08-22T14:26:44.987654Z|WRN|rule2
2025-08-22T14:26:50.142178Z|ERR|rule3
""".lstrip().splitlines()


class ParserWithBase(LogParser):
    BASE_PATTERN = "".join(
        f"{s}+\\|"
        for s in [
            "(?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z)",
            "(?P<level>DBG|INF|WRN|ERR)",
        ]
    )

    @dataclasses.dataclass
    class Entry:
        timestamp: datetime.datetime
        level: str

        def __init__(self, m: re.Match):
            self.timestamp = datetime.datetime.strptime(
                m.group("timestamp"),
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )
            self.level = m.group("level")

    def __init__(self) -> None:
        super().__init__()
        self.r1: Optional[ParserWithBase.Entry] = None
        self.r2: Optional[ParserWithBase.Entry] = None

    @rule("rule1")
    def rule1(self, m: re.Match) -> None:
        self.r1 = self.Entry(m)

    @rule("rule2")
    def rule2(self, m: re.Match) -> None:
        self.r2 = self.Entry(m)


def test_base_pattern() -> None:
    p = ParserWithBase()
    p.run(DATA_WITH_BASE)
    assert p.r1
    assert p.r1.level == "INF"
    assert p.r2
    assert p.r2.level == "WRN"
    assert 4 < (p.r2.timestamp - p.r1.timestamp).total_seconds() < 5


def test_inherited_base_pattern() -> None:
    class Sub(ParserWithBase):
        def __init__(self) -> None:
            super().__init__()
            self.r3: Optional[ParserWithBase.Entry] = None

        @rule("rule3")
        def rule3(self, m: re.Match) -> None:
            self.r3 = self.Entry(m)

    p = Sub()
    p.run(DATA_WITH_BASE)
    assert p.r3
    assert p.r3.level == "ERR"
    assert p.r2
    assert 5 < (p.r3.timestamp - p.r2.timestamp).total_seconds() < 6
