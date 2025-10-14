import base64
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, SecretBytes, SecretStr


class InspectMixin:
    _secret_type_marker = (SecretStr, SecretBytes)
    _secret_field_pattern = re.compile(r"(?i)\b(pass(word)?|secret|token|key|cred(ential)?)\b")
    _id_field_pattern = re.compile(r"\bid\b")

    def inspect(self, show_secrets: bool = False, json_safe: bool = False) -> dict[str, Any]:
        """
        Walk all model_fields, masking or revealing based on `show_secrets`.
        If `json_safe` is True, coerce non-JSON-serializable types (e.g., datetime)
        into JSON-safe primitives (str, int, float, bool, None, list, dict).
        """
        out = {
            name: self._inspect_value(getattr(self, name), name, show_secrets, json_safe)
            for name in getattr(self, "model_fields", {})  # pydantic v2
            if name != "id"
        }
        return out

    # ---- helpers -----------------------------------------------------------------

    def _to_json_safe(self, value: Any) -> Any:
        """Best-effort conversion of common Python types to JSON-safe primitives."""
        # datetime-like
        if isinstance(value, datetime | date | time):
            # Ensure aware datetimes stay aware; naive -> assume UTC to be explicit
            if isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()

        # timedeltas -> ISO 8601 duration-ish or total seconds; prefer ISO-ish string
        if isinstance(value, timedelta):
            # serialize as total seconds to avoid custom parsers
            return value.total_seconds()

        # numbers/ids/enums/paths
        if isinstance(value, UUID | Path):
            return str(value)

        if isinstance(value, Decimal):
            # Use string to avoid precision loss; callers can cast if needed
            return str(value)

        if isinstance(value, Enum):
            # Use .value which is typically JSON-safe
            return self._to_json_safe(value.value)

        # bytes-like: base64 for portability
        if isinstance(value, bytes | bytearray | memoryview):
            return base64.b64encode(bytes(value)).decode("ascii")

        return value

    # -----------------------------------------------------------------------------

    def _inspect_value(
        self,
        value: Any,
        field_name: str = "",
        show_secrets: bool = False,
        json_safe: bool = False,
    ) -> Any:
        # 1) Pydantic Secret types
        if isinstance(value, self._secret_type_marker):
            if show_secrets:
                raw = value.get_secret_value()
                return self._to_json_safe(raw) if json_safe else raw
            return "<secret>"

        # 2) secret-like field names
        if field_name and self._secret_field_pattern.search(field_name) and not show_secrets:
            return "<hidden>"

        # 3) nested Pydantic models and mixins
        if isinstance(value, InspectMixin):
            return value.inspect(show_secrets=show_secrets, json_safe=json_safe)

        if isinstance(value, BaseModel):
            # Use the same logic recursively for arbitrary pydantic models
            nested = {
                name: self._inspect_value(getattr(value, name), name, show_secrets, json_safe)
                for name in getattr(value, "model_fields", {})
                if name != "id"
            }
            return nested

        # 4) dicts: skip raw bytes unless json_safe handles them
        if isinstance(value, dict):
            out: dict[Any, Any] = {}
            for k, v in value.items():
                if not json_safe and isinstance(v, bytes | bytearray):
                    # keep original behavior of skipping raw bytes in dicts
                    continue
                out[str(k)] = self._inspect_value(v, str(k), show_secrets, json_safe)
            return out

        # 5) sequences: list, tuple, set
        if isinstance(value, list | tuple | set):
            return [self._inspect_value(item, "", show_secrets, json_safe) for item in value]

        # 6) everything else (possibly coerce to JSON-safe)
        return self._to_json_safe(value) if json_safe else value
