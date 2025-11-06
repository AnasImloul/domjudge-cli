from __future__ import annotations

import datetime as dt
import os
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Generic, TypeVar


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

    def __init__(self, parser: Callable[[str], T] | None = None):
        self._parser: Callable[[str], T] = parser or (lambda s: s)  # type: ignore
        self._transforms: list[Callable[[T], T]] = []
        self._checks: list[Callable[[T], None]] = []

    # ---- pipeline primitives ----
    def parse(self, parser: Callable[[str], U]) -> ValidatorBuilder[U]:
        """Switch the parser, resetting the output type to U.
        Keeps existing transforms/checks by capturing the current pipeline
        into a single new parser so chaining remains intuitive.
        """
        prev = self.build()

        def new_parser(s: str) -> U:
            # run the existing pipeline first to get T, then coerce to U via parser
            t_value = prev(s)  # may raise Invalid
            try:
                return parser(t_value if isinstance(t_value, str) else str(t_value))
            except Invalid:
                raise
            except Exception as e:
                raise Invalid("Invalid value.") from e

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
            except Exception as e:
                raise Invalid("Invalid value.") from e

        return ValidatorBuilder(new_parser)  # type: ignore[return-value]

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
    def string(cls, *, none_as_empty: bool = False, coerce: bool = False) -> StringBuilder:
        return StringBuilder(none_as_empty=none_as_empty, coerce=coerce)

    # --------------------------------------------------------
    # Number helpers (int/float)
    # --------------------------------------------------------
    @classmethod
    def integer(cls) -> NumberBuilder[int]:
        return NumberBuilder(int, kind_name="integer")

    @classmethod
    def floating(cls) -> NumberBuilder[float]:
        return NumberBuilder(float, kind_name="number")

    # --------------------------------------------------------
    # Specific parsers
    # --------------------------------------------------------
    @classmethod
    def datetime(cls, fmt: str = "%Y-%m-%d %H:%M:%S") -> DateTimeBuilder:
        return DateTimeBuilder(fmt)

    @classmethod
    def duration_hms(cls) -> DurationBuilder:
        return DurationBuilder()

    @classmethod
    def path(cls) -> PathBuilder:
        return PathBuilder()

    @classmethod
    def port(cls) -> PortBuilder:
        return PortBuilder()


# ------------------------------------------------------------
# StringBuilder
# ------------------------------------------------------------
class StringBuilder(ValidatorBuilder[str]):
    def __init__(self, *, none_as_empty: bool = False, coerce: bool = False):
        def _parse(s) -> str:
            # Handle None first
            if s is None:
                if none_as_empty:
                    return ""
                raise Invalid("Should be a string.")
            # Enforce/optionally coerce non-strings
            if not isinstance(s, str):
                if coerce:
                    try:
                        return str(s)
                    except Exception as e:
                        raise Invalid("Should be a string.") from e
                raise Invalid("Should be a string.")
            return s

        super().__init__(parser=_parse)

    # transforms
    def strip(self) -> StringBuilder:
        return self.transform(lambda s: s.strip())

    def lower(self) -> StringBuilder:
        return self.transform(lambda s: s.lower())

    def upper(self) -> StringBuilder:
        return self.transform(lambda s: s.upper())

    def replace(self, _from: str, _to: str) -> StringBuilder:
        return self.transform(lambda s: s.replace(_from, _to))

    def repr(self) -> StringBuilder:
        return self.transform(lambda s: repr(s))

    # checks
    def non_empty(self, message: str = "This field cannot be empty.") -> StringBuilder:
        return self.check(lambda s: bool(s.strip()), message)

    def min_length(self, n: int) -> StringBuilder:
        return self.check(lambda s: len(s) >= n, f"Must be at least {n} characters.")

    def max_length(self, n: int) -> StringBuilder:
        return self.check(lambda s: len(s) <= n, f"Must be at most {n} characters.")

    def matches(self, pattern: str, flags: int = 0, message: str | None = None) -> StringBuilder:
        rx = re.compile(pattern, flags)
        msg = message or f"Value does not match pattern {pattern!r}."
        return self.check(lambda s: bool(rx.fullmatch(s)), msg)

    def one_of(self, options: Iterable[str]) -> StringBuilder:
        opts = set(options)
        formatted = ", ".join(repr(choice) for choice in sorted(opts))
        return self.check(lambda s: s in opts, f"Must be one of: {formatted}.")


# ------------------------------------------------------------
# NumberBuilder
# ------------------------------------------------------------
class NumberBuilder(ValidatorBuilder[Number], Generic[Number]):
    def __init__(self, caster: Callable[[str], Number], *, kind_name: str = "number"):
        # Robust parse with good error messages
        def _parse(s: str) -> Number:
            try:
                return caster(s.strip())
            except Exception as e:
                raise Invalid(f"Must be a {kind_name}.") from e

        super().__init__(parser=_parse)  # type: ignore[arg-type]

    # checks
    def min(self, lo: Number) -> NumberBuilder[Number]:
        return self.check(lambda n: n >= lo, f"Must be \u2265 {lo}.")

    def max(self, hi: Number) -> NumberBuilder[Number]:
        return self.check(lambda n: n <= hi, f"Must be \u2264 {hi}.")

    def positive(self) -> NumberBuilder[Number]:
        return self.check(lambda n: n > 0, "Must be a positive number.")

    def non_negative(self) -> NumberBuilder[Number]:
        return self.check(lambda n: n >= 0, "Must be a non-negative number.")

    def one_of(self, options: Iterable[Number]) -> NumberBuilder[Number]:
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
            except ValueError as e:
                raise Invalid(f"Invalid date/time. Use {fmt}") from e

        super().__init__(parser=_parse)
        self._fmt = fmt

    def between(
        self,
        *,
        min_dt: dt.datetime | None = None,
        max_dt: dt.datetime | None = None,
    ) -> DateTimeBuilder:
        if min_dt is not None:
            self.check(lambda d: d >= min_dt, f"Must be on/after {min_dt.strftime(self._fmt)}.")
        if max_dt is not None:
            self.check(lambda d: d <= max_dt, f"Must be on/before {max_dt.strftime(self._fmt)}.")
        return self


# ------------------------------------------------------------
# Duration HH:MM:SS -> (h, m, s)
# ------------------------------------------------------------
class DurationBuilder(ValidatorBuilder[tuple[int, int, int]]):
    def __init__(self):
        def _parse(s: str) -> tuple[int, int, int]:
            try:
                h, m, sec = map(int, s.split(":"))
            except Exception as e:
                raise Invalid("Duration must be HH:MM:SS") from e
            if h == m == sec == 0:
                raise Invalid("Duration must be greater than 0 seconds.")
            return h, m, sec

        super().__init__(parser=_parse)


# ------------------------------------------------------------
# Path (string)
# ------------------------------------------------------------
class PathBuilder(ValidatorBuilder[str]):
    def __init__(self):
        super().__init__(parser=lambda s: s.strip())

    # ---- reusable checks ----
    def must_exist(self) -> PathBuilder:
        return self.check(os.path.exists, "Path does not exist.")

    def must_be_file(self) -> PathBuilder:
        return self.check(os.path.isfile, "Path is not a file.")

    def must_be_dir(self) -> PathBuilder:
        return self.check(os.path.isdir, "Path is not a directory.")

    def allowed_extensions(self, exts: Iterable[str]) -> PathBuilder:
        allowed = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
        formatted = ", ".join(repr(e) for e in sorted(allowed))
        return self.check(
            lambda p: Path(p).suffix.lower() in allowed,
            f"Unsupported extension. Must be one of: {formatted}.",
        )

    def normalize(self) -> PathBuilder:
        """Expand `~` and return absolute real path."""
        return self.transform(lambda p: str(Path(p).expanduser().resolve()))


# ------------------------------------------------------------
# Port validator
# ------------------------------------------------------------
class PortBuilder(NumberBuilder[int]):
    """Specialized validator for network port numbers."""

    def __init__(self):
        super().__init__(int, kind_name="port number")
        # Standard port validation
        self.min(1).max(65535)

    def unprivileged(
        self,
        message: str = "Port below 1024 requires elevated privileges. Consider using ports >= 1024",
    ) -> PortBuilder:
        """Ensure port is >= 1024 (doesn't require root)."""
        return self.check(lambda p: p >= 1024, message)

    def high_port(self) -> PortBuilder:
        """Ensure port is in high/dynamic range (>= 49152)."""
        return self.min(49152)  # type: ignore[return-value]

    def registered_port(self) -> PortBuilder:
        """Ensure port is in registered range (1024-49151)."""
        return self.min(1024).max(49151)  # type: ignore[return-value]
