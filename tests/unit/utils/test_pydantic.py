"""Tests for InspectMixin in dom.utils.pydantic."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, SecretBytes, SecretStr

from dom.utils.pydantic import InspectMixin


class _Color(str, Enum):
    RED = "red"


class _Plain(InspectMixin, BaseModel):
    name: str
    value: int


class _WithSecrets(InspectMixin, BaseModel):
    username: str
    password: SecretStr  # masked by Secret type
    token: str  # masked by field-name pattern (whole-word match on 'token')
    token_bytes: SecretBytes


class _Nested(InspectMixin, BaseModel):
    label: str
    inner: _Plain


class _NestedBaseModel(BaseModel):
    """Plain BaseModel (no InspectMixin) used as a nested field."""

    name: str
    password: SecretStr


class _Wrapper(InspectMixin, BaseModel):
    title: str
    nested: _NestedBaseModel


class _WithJsonAwkwardTypes(InspectMixin, BaseModel):
    when: datetime
    where: Path
    uid: UUID
    money: Decimal
    color: _Color
    payload: bytes


class _WithCollections(InspectMixin, BaseModel):
    tags: list[str]
    meta: dict[str, str | bytes]


class _WithId(InspectMixin, BaseModel):
    id: str
    name: str


class TestInspectBasics:
    def test_plain_fields_pass_through(self):
        out = _Plain(name="foo", value=7).inspect()
        assert out == {"name": "foo", "value": 7}

    def test_excludes_id_field(self):
        out = _WithId(id="abc", name="thing").inspect()
        assert out == {"name": "thing"}


class TestInspectSecrets:
    def test_secret_types_masked_by_default(self):
        m = _WithSecrets(
            username="alice",
            password=SecretStr("hunter2"),
            token="REVEAL-ME",
            token_bytes=SecretBytes(b"raw-token"),
        )
        out = m.inspect()

        # Pydantic Secret types -> "<secret>"
        assert out["password"] == "<secret>"
        assert out["token_bytes"] == "<secret>"
        # field-name pattern (whole-word 'token') -> "<hidden>"
        assert out["token"] == "<hidden>"
        # non-secret field unaffected
        assert out["username"] == "alice"

    def test_show_secrets_reveals_underlying_values(self):
        m = _WithSecrets(
            username="alice",
            password=SecretStr("hunter2"),
            token="REVEAL-ME",
            token_bytes=SecretBytes(b"raw-token"),
        )
        out = m.inspect(show_secrets=True)

        assert out["password"] == "hunter2"
        assert out["token_bytes"] == b"raw-token"
        # field-name pattern only masks when show_secrets=False
        assert out["token"] == "REVEAL-ME"


class TestInspectNested:
    def test_nested_inspect_mixin_recurses(self):
        m = _Nested(label="outer", inner=_Plain(name="inside", value=1))
        out = m.inspect()
        assert out == {"label": "outer", "inner": {"name": "inside", "value": 1}}

    def test_nested_plain_basemodel_walks_fields(self):
        m = _Wrapper(title="t", nested=_NestedBaseModel(name="n", password=SecretStr("s")))
        out = m.inspect()
        # secret on the nested BaseModel still gets masked
        assert out == {"title": "t", "nested": {"name": "n", "password": "<secret>"}}


class TestInspectJsonSafe:
    def test_coerces_awkward_types_when_json_safe(self):
        m = _WithJsonAwkwardTypes(
            when=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
            where=Path("/tmp/x"),
            uid=UUID("12345678-1234-5678-1234-567812345678"),
            money=Decimal("3.14"),
            color=_Color.RED,
            payload=b"abc",
        )
        out = m.inspect(json_safe=True)

        assert out["when"] == "2026-05-06T12:00:00+00:00"
        assert out["where"] == "/tmp/x"
        assert out["uid"] == "12345678-1234-5678-1234-567812345678"
        assert out["money"] == "3.14"
        assert out["color"] == "red"
        assert out["payload"] == "YWJj"  # base64("abc")


class TestInspectCollections:
    def test_lists_and_dicts_are_walked(self):
        m = _WithCollections(tags=["a", "b"], meta={"k": "v"})
        out = m.inspect()
        assert out == {"tags": ["a", "b"], "meta": {"k": "v"}}

    def test_raw_bytes_dropped_from_dict_when_not_json_safe(self):
        """Without json_safe, bytes values inside dicts are skipped (legacy behavior)."""
        m = _WithCollections(tags=[], meta={"text": "ok", "blob": b"\x00\x01"})
        out = m.inspect()
        assert out["meta"] == {"text": "ok"}
