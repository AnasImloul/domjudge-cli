import re
from typing import Any, Dict

from pydantic import SecretStr, SecretBytes

class InspectMixin:
    _secret_type_marker = (SecretStr, SecretBytes)
    _secret_field_pattern = re.compile(r"(?i)\b(pass(word)?|secret|token|key|cred(ential)?)\b")

    def inspect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for name, field in self.model_fields.items():
            value = getattr(self, name)

            # 1) Mask any Pydantic Secret types outright
            if isinstance(value, self._secret_type_marker):
                result[name] = "<secret>"
                continue

            # 2) Mask anything whose field‐name suggests it's secret
            if self._secret_field_pattern.search(name):
                result[name] = "<hidden>"
                continue

            # 3) Recurse into nested InspectMixin
            if isinstance(value, InspectMixin):
                result[name] = value.inspect()
                continue

            # 4) For dicts of raw bytes (e.g. files), show only the filenames
            if isinstance(value, dict) and all(isinstance(v, (bytes, bytearray)) for v in value.values()):
                result[name] = list(value.keys())
                continue

            # 5) Otherwise, just return the raw value
            result[name] = value

        return result