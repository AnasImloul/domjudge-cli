"""Tests for validation rules."""

import pytest

from dom.utils.validators import Invalid
from dom.validation.rules import ValidationRules


class TestPortValidation:
    """Tests for port validation."""

    def test_valid_ports(self):
        """Test that valid port numbers pass validation."""
        # By default, warns about privileged ports (< 1024)
        validator = ValidationRules.port().build()

        # Test non-privileged ports
        assert validator("1024") == 1024
        assert validator("8080") == 8080
        assert validator("65535") == 65535

        # Test with privileged ports allowed
        validator_with_privileged = ValidationRules.port(warn_privileged=False).build()
        assert validator_with_privileged("80") == 80
        assert validator_with_privileged("443") == 443

    def test_invalid_ports(self):
        """Test that invalid port numbers fail validation."""
        validator = ValidationRules.port().build()

        with pytest.raises(Invalid):
            validator("0")

        with pytest.raises(Invalid):
            validator("65536")

        with pytest.raises(Invalid):
            validator("-1")


class TestContestNameValidation:
    """Tests for contest name validation."""

    def test_valid_names(self):
        """Test that valid contest names pass validation."""
        validator = ValidationRules.contest_name().build()

        assert validator("Test Contest") == "Test Contest"
        assert validator("  Trimmed  ") == "Trimmed"

    def test_empty_name_fails(self):
        """Test that empty contest name fails validation."""
        validator = ValidationRules.contest_name().build()

        with pytest.raises(Invalid, match="cannot be empty"):
            validator("")

        with pytest.raises(Invalid, match="cannot be empty"):
            validator("   ")

    def test_too_long_name_fails(self):
        """Test that too long name fails validation."""
        validator = ValidationRules.contest_name().build()

        with pytest.raises(Invalid):
            validator("x" * 101)


class TestContestShortnameValidation:
    """Tests for contest shortname validation."""

    def test_valid_shortnames(self):
        """Test that valid shortnames pass validation."""
        validator = ValidationRules.contest_shortname().build()

        assert validator("TEST2025") == "TEST2025"
        assert validator("test2025") == "TEST2025"  # Uppercased
        assert validator("TEST_2025") == "TEST_2025"
        assert validator("TEST-2025") == "TEST-2025"

    def test_invalid_characters_fail(self):
        """Test that invalid characters fail validation."""
        validator = ValidationRules.contest_shortname().build()

        with pytest.raises(Invalid, match="can only contain"):
            validator("TEST 2025")  # Space not allowed

        with pytest.raises(Invalid, match="can only contain"):
            validator("TEST@2025")  # Special char not allowed


class TestPasswordValidation:
    """Tests for password validation."""

    def test_valid_passwords(self):
        """Test that valid passwords pass validation."""
        validator = ValidationRules.password().build()

        assert validator("password123") == "password123"
        assert validator("VeryLongPassword123!@#") == "VeryLongPassword123!@#"

    def test_too_short_password_fails(self):
        """Test that too short password fails validation."""
        validator = ValidationRules.password().build()

        with pytest.raises(Invalid):
            validator("short")  # < 8 characters

    def test_too_long_password_fails(self):
        """Test that too long password fails validation."""
        validator = ValidationRules.password().build()

        with pytest.raises(Invalid):
            validator("x" * 129)  # > 128 characters


class TestDurationValidation:
    """Tests for duration format validation."""

    def test_valid_durations(self):
        """Test that valid duration formats pass validation."""
        validator = ValidationRules.duration().build()

        assert validator("5:00:00") == "5:00:00"
        assert validator("5:30:45") == "5:30:45"
        assert validator("10:00:00.000") == "10:00:00.000"

    def test_invalid_durations(self):
        """Test that invalid duration formats fail validation."""
        validator = ValidationRules.duration().build()

        with pytest.raises(Invalid, match="format"):
            validator("5:00")  # Missing seconds

        with pytest.raises(Invalid, match="format"):
            validator("5:0:0")  # Missing leading zeros

        with pytest.raises(Invalid, match="format"):
            validator("invalid")


class TestEmailValidation:
    """Tests for email validation."""

    def test_valid_emails(self):
        """Test that valid email addresses pass validation."""
        validator = ValidationRules.email().build()

        assert validator("test@example.com") == "test@example.com"
        assert validator("TEST@EXAMPLE.COM") == "test@example.com"  # Lowercased
        assert validator("user.name@example.co.uk") == "user.name@example.co.uk"

    def test_invalid_emails(self):
        """Test that invalid email addresses fail validation."""
        validator = ValidationRules.email().build()

        with pytest.raises(Invalid, match="Invalid email"):
            validator("not-an-email")

        with pytest.raises(Invalid, match="Invalid email"):
            validator("@example.com")

        with pytest.raises(Invalid, match="Invalid email"):
            validator("user@")


class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_urls(self):
        """Test that valid URLs pass validation."""
        validator = ValidationRules.url().build()

        assert validator("http://localhost:8080") == "http://localhost:8080"
        assert validator("https://example.com") == "https://example.com"
        assert validator("http://192.168.1.1:8080/path") == "http://192.168.1.1:8080/path"

    def test_invalid_urls(self):
        """Test that invalid URLs fail validation."""
        validator = ValidationRules.url().build()

        with pytest.raises(Invalid, match="Invalid URL"):
            validator("not-a-url")

        with pytest.raises(Invalid, match="Invalid URL"):
            validator("ftp://example.com")  # Wrong protocol
