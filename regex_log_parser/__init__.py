import collections
import dataclasses
import re
from typing import Any, Callable, Dict, Iterable, Tuple, Type, TypeVar

T = TypeVar("T", bound="LogParser")

_RuleFn = Callable[[T, re.Match], None]


@dataclasses.dataclass
class _PreRule:
    pattern: str
    fn: _RuleFn


@dataclasses.dataclass
class _Rule:
    regex: re.Pattern
    fn: _RuleFn


def rule(pattern: str) -> Callable[[_RuleFn], _PreRule]:
    def wrapper(fn: _RuleFn) -> _PreRule:
        return _PreRule(pattern=pattern, fn=fn)

    return wrapper


LPMT = TypeVar("LPMT", bound="_LogParserMeta")


class _LogParserMeta(type):
    @staticmethod
    def _getattr_ext(
        attr: str,
        bases: Tuple[type, ...],
        clsdict: Dict[str, Any],
        default: Any = None,
    ) -> Any:
        try:
            return clsdict[attr]
        except KeyError:
            for base in bases:
                try:
                    return getattr(base, attr)
                except AttributeError:
                    pass
            if default is not None:
                return default
            raise KeyError(attr)

    def __new__(
        cls: Type[LPMT],
        clsname: str,
        bases: Tuple[type, ...],
        clsdict: Dict[str, Any],
    ) -> LPMT:
        rules: Dict[str, _Rule] = cls._getattr_ext(
            "_lpm_rules",
            bases,
            clsdict,
            {},
        ).copy()
        base = cls._getattr_ext("BASE_PATTERN", bases, clsdict)
        for k, v in clsdict.items():
            if isinstance(v, _PreRule):
                rules[k] = _Rule(
                    regex=re.compile(f"{base}.*" + v.pattern),
                    fn=v.fn,
                )
        clsdict["_lpm_rules"] = rules
        return super().__new__(cls, clsname, bases, clsdict)


class LogParser(metaclass=_LogParserMeta):
    BASE_PATTERN = ""

    _lpm_rules: Dict[str, _Rule]

    def __init__(self) -> None:
        self.hits: Dict[str, int] = collections.defaultdict(int)

    def run(self, lines: Iterable[str]) -> None:
        for line in lines:
            for key, rule in self._lpm_rules.items():
                m = rule.regex.match(line)
                if m:
                    self.hits[key] += 1
                    rule.fn(self, m)
