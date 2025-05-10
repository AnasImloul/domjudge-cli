import re
from typing import Any, Dict

from pydantic import SecretStr, SecretBytes, BaseModel

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
                return value.get_secret_value()
            return "<secret>"

        # 2) secret-like field names
        if field_name and self._secret_field_pattern.search(field_name):
            if not show_secrets:
                return "<hidden>"

        # 3) nested Pydantic models and mixins
        if isinstance(value, (InspectMixin, BaseModel)):
            return value.inspect(show_secrets=show_secrets)

        # 4) dicts: skip raw bytes, recurse
        if isinstance(value, dict):
            out: Dict[Any, Any] = {}
            for k, v in value.items():
                if isinstance(v, (bytes, bytearray)):
                    continue
                out[k] = self._inspect_value(v, str(k), show_secrets)
            return out

        # 5) sequences: list, tuple, set
        if isinstance(value, (list, tuple, set)):
            return [self._inspect_value(item, "", show_secrets) for item in value]

        # 6) everything else
        return value
