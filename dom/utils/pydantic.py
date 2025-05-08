import re
from typing import Any, Dict
from collections.abc import Iterable

from pydantic import SecretStr, SecretBytes

class InspectMixin:
    _secret_type_marker = (SecretStr, SecretBytes)
    _secret_field_pattern = re.compile(r"(?i)\b(pass(word)?|secret|token|key|cred(ential)?)\b")
    _id_field_pattern = re.compile(r"\bid\b")

    def inspect(self, show_secrets: bool = False) -> Dict[str, Any]:
        """
        Walk all model_fields, masking or revealing based on `show_secrets`.
        """
        return {
            name: self._inspect_value(getattr(self, name), name, show_secrets)
            for name in self.model_fields if name != "id"
        }

    def _inspect_value(
        self, value: Any, field_name: str = "", show_secrets: bool = False
    ) -> Any:
        # 1) Pydantic Secret types
        if isinstance(value, self._secret_type_marker):
            if show_secrets:
                # actually reveal it
                return value.get_secret_value()
            return "<secret>"

        # 2) secret-like field names
        if field_name and self._secret_field_pattern.search(field_name):
            if not show_secrets:
                return "<hidden>"
            # else, fall through and show raw

        # 3) nested mixins
        if isinstance(value, InspectMixin):
            return value.inspect(show_secrets=show_secrets)

        # 4) dicts: skip raw bytes, recurse into secrets or mixins
        if isinstance(value, dict):
            out: Dict[Any, Any] = {}
            for k, v in value.items():
                if isinstance(v, (bytes, bytearray)):
                    continue
                out[k] = self._inspect_value(v, str(k), show_secrets)
            return out

        # 5) other iterables (but not str/bytes/dict)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, dict)):
            return [self._inspect_value(item, "", show_secrets) for item in value]

        # 6) everything else
        return value
