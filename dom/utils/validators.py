from __future__ import annotations
import datetime as dt
import os
import re
from typing import Any, Callable, Generic, Iterable, Optional, Tuple, TypeVar

# --- Reuse the user's Invalid error type ---
class Invalid(Exception):
    pass

T = TypeVar("T")
U = TypeVar("U")
Number = TypeVar("Number", int, float)

S = TypeVar("S", bound="ValidatorBuilder")

# ------------------------------------------------------------
# Core pipeline
# ------------------------------------------------------------
class ValidatorBuilder(Generic[T]):
    """A small, chainable validator/builder that compiles to a single function.

    The pipeline looks like:  str -> parser -> (zero+ transforms) -> checks -> T

    - The parser converts the input string to a value of type T (default: identity)
    - Transforms are applied in the order they were added
    - Checks run after all parsing/transforms and should raise Invalid on failure

    Call .build() to get the final function:  (str) -> T
    """

    def __init__(self, parser: Optional[Callable[[str], T]] = None):
        self._parser: Callable[[str], T] = parser or (lambda s: s)  # type: ignore
        self._transforms: list[Callable[[T], T]] = []
        self._checks: list[Callable[[T], None]] = []

    # ---- pipeline primitives ----
    def parse(self, parser: Callable[[str], U]) -> "ValidatorBuilder[U]":
        """Switch the parser, resetting the output type to U.
        Keeps existing transforms/checks by capturing the current pipeline
        into a single new parser so chaining remains intuitive.
        """
        prev = self.build()

        def new_parser(s: str) -> U:
            # run the existing pipeline first to get T, then coerce to U via parser
            t_value = prev(s)  # may raise Invalid
            try:
                return parser(t_value if isinstance(t_value, str) else str(t_value))  # type: ignore
            except Invalid:
                raise
            except Exception:
                raise Invalid("Invalid value.")

        # return a fresh builder with the new parser and no transforms/checks yet
        return ValidatorBuilder(new_parser)

    def map(self: S, fn: Callable[[T], U]) -> S:
        prev = self.build()

        def new_parser(s: str) -> U:
            v_t = prev(s)
            try:
                return fn(v_t)
            except Invalid:
                raise
            except Exception:
                raise Invalid("Invalid value.")

        return ValidatorBuilder(new_parser)

    def transform(self: S, fn: Callable[[T], T]) -> S:
        self._transforms.append(fn)
        return self

    def check(self: S, predicate: Callable[[T], bool], message: str) -> S:
        def _c(v: T) -> None:
            if not predicate(v):
                raise Invalid(message)
        self._checks.append(_c)
        return self

    def satisfy(self: S, fn: Callable[[T], None]) -> S:
        """Add a check that raises Invalid on failure itself."""
        self._checks.append(fn)
        return self

    def build(self) -> Callable[[str], T]:
        def _f(s: str) -> T:
            v = self._parser(s)
            for tr in self._transforms:
                v = tr(v)
            for chk in self._checks:
                chk(v)
            return v
        return _f

    # --------------------------------------------------------
    # String helpers
    # --------------------------------------------------------
    @classmethod
    def string(cls) -> "StringBuilder":
        return StringBuilder()

    # --------------------------------------------------------
    # Number helpers (int/float)
    # --------------------------------------------------------
    @classmethod
    def integer(cls) -> "NumberBuilder[int]":
        return NumberBuilder(int, kind_name="integer")

    @classmethod
    def floating(cls) -> "NumberBuilder[float]":
        return NumberBuilder(float, kind_name="number")

    # --------------------------------------------------------
    # Specific parsers
    # --------------------------------------------------------
    @classmethod
    def datetime(cls, fmt: str = "%Y-%m-%d %H:%M:%S") -> "DateTimeBuilder":
        return DateTimeBuilder(fmt)

    @classmethod
    def duration_hms(cls) -> "DurationBuilder":
        return DurationBuilder()

    @classmethod
    def teams_file(cls) -> "TeamsFileBuilder":
        return TeamsFileBuilder()


# ------------------------------------------------------------
# StringBuilder
# ------------------------------------------------------------
class StringBuilder(ValidatorBuilder[str]):
    def __init__(self):
        super().__init__(parser=lambda s: s)

    # transforms
    def strip(self) -> "StringBuilder":
        return self.transform(lambda s: s.strip())

    def lower(self) -> "StringBuilder":
        return self.transform(lambda s: s.lower())

    def upper(self) -> "StringBuilder":
        return self.transform(lambda s: s.upper())

    # checks
    def non_empty(self, message: str = "This field cannot be empty.") -> "StringBuilder":
        return self.check(lambda s: bool(s.strip()), message)

    def min_length(self, n: int) -> "StringBuilder":
        return self.check(lambda s: len(s) >= n, f"Must be at least {n} characters.")

    def max_length(self, n: int) -> "StringBuilder":
        return self.check(lambda s: len(s) <= n, f"Must be at most {n} characters.")

    def matches(self, pattern: str, flags: int = 0, message: Optional[str] = None) -> "StringBuilder":
        rx = re.compile(pattern, flags)
        msg = message or f"Value does not match pattern {pattern!r}."
        return self.check(lambda s: bool(rx.fullmatch(s)), msg)

    def one_of(self, options: Iterable[str]) -> "StringBuilder":
        opts = set(options)
        return self.check(lambda s: s in opts, f"Must be one of: {', '.join(sorted(opts))}.")


# ------------------------------------------------------------
# NumberBuilder
# ------------------------------------------------------------
class NumberBuilder(ValidatorBuilder[Number], Generic[Number]):
    def __init__(self, caster: Callable[[str], Number], *, kind_name: str = "number"):
        # Robust parse with good error messages
        def _parse(s: str) -> Number:
            try:
                return caster(s.strip())
            except Exception:
                raise Invalid(f"Must be a {kind_name}.")
        super().__init__(parser=_parse)

    # checks
    def min(self, lo: Number) -> "NumberBuilder[Number]":
        return self.check(lambda n: n >= lo, f"Must be \u2265 {lo}.")

    def max(self, hi: Number) -> "NumberBuilder[Number]":
        return self.check(lambda n: n <= hi, f"Must be \u2264 {hi}.")

    def positive(self) -> "NumberBuilder[Number]":
        return self.check(lambda n: n > 0, "Must be a positive number.")

    def non_negative(self) -> "NumberBuilder[Number]":
        return self.check(lambda n: n >= 0, "Must be a non-negative number.")

    def one_of(self, options: Iterable[Number]) -> "NumberBuilder[Number]":
        opts = set(options)
        return self.check(lambda n: n in opts, f"Must be one of: {sorted(opts)}.")


# ------------------------------------------------------------
# Datetime builder
# ------------------------------------------------------------
class DateTimeBuilder(ValidatorBuilder[dt.datetime]):
    def __init__(self, fmt: str):
        def _parse(s: str) -> dt.datetime:
            try:
                return dt.datetime.strptime(s.strip(), fmt)
            except ValueError:
                raise Invalid(f"Invalid date/time. Use {fmt}")
        super().__init__(parser=_parse)
        self._fmt = fmt

    def between(
        self,
        *,
        min_dt: Optional[dt.datetime] = None,
        max_dt: Optional[dt.datetime] = None,
    ) -> "DateTimeBuilder":
        if min_dt is not None:
            self.check(lambda d: d >= min_dt, f"Must be on/after {min_dt.strftime(self._fmt)}.")
        if max_dt is not None:
            self.check(lambda d: d <= max_dt, f"Must be on/before {max_dt.strftime(self._fmt)}.")
        return self


# ------------------------------------------------------------
# Duration HH:MM:SS -> (h, m, s)
# ------------------------------------------------------------
class DurationBuilder(ValidatorBuilder[Tuple[int, int, int]]):
    def __init__(self):
        def _parse(s: str) -> Tuple[int, int, int]:
            try:
                h, m, sec = map(int, s.split(":"))
            except Exception:
                raise Invalid("Duration must be HH:MM:SS")
            if h == m == sec == 0:
                raise Invalid("Duration must be greater than 0 seconds.")
            return h, m, sec
        super().__init__(parser=_parse)


# ------------------------------------------------------------
# Teams file -> (path, delimiter)
# ------------------------------------------------------------
class TeamsFileBuilder(ValidatorBuilder[tuple[str, str]]):
    def __init__(self):
        def _parse(s: str) -> tuple[str, str]:
            path = s.strip()
            if not os.path.isfile(path):
                raise Invalid(f"File '{path}' does not exist.")
            ext = os.path.splitext(path)[1].lower()
            if ext not in (".csv", ".tsv"):
                raise Invalid(f"Unsupported extension '{ext}'. Use .csv or .tsv")
            default_delim = "\t" if ext == ".tsv" else ","
            return path, default_delim
        super().__init__(parser=_parse)

    def normalize_delimiter(self, user_value: str) -> "ValidatorBuilder[tuple[str, str]]":
        def _norm(current: tuple[str, str]) -> tuple[str, str]:
            path, default = current
            s = user_value.strip()
            if not s:
                return path, default
            lowers = s.lower()
            if lowers in ("tab", "\\t"):
                return path, "\t"
            if lowers in ("comma", ","):
                return path, ","
            if lowers in ("semicolon", ";"):
                return path, ";"
            if len(s) > 1 and s not in (",", ";", "\t"):
                raise Invalid("Delimiter must be a single character (or 'tab', 'comma', 'semicolon').")
            return path, s
        return self.map(_norm)


def normalize_delimiter(s: str, default: str) -> str:
    s = s.strip()
    if not s:
        return default
    lowers = s.lower()
    if lowers in ("tab", "\\t"):
        return "\t"
    if lowers in ("comma", ","):
        return ","
    if lowers in ("semicolon", ";"):
        return ";"
    if len(s) > 1 and s not in (",", ";", "\t"):
        # keep it tight; avoid accidental long strings
        raise Invalid("Delimiter must be a single character (or 'tab', 'comma', 'semicolon').")
    return s
