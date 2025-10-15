"""Tests for problem utility functions."""

from unittest.mock import Mock

import pytest

from dom.types.problem import ProblemPackage
from dom.utils.problem import assign_problem_letter, assign_problem_letters


class TestAssignProblemLetter:
    """Tests for problem letter assignment."""

    def test_single_letters(self):
        """Test single letter assignment (A-Z)."""
        assert assign_problem_letter(0) == "A"
        assert assign_problem_letter(1) == "B"
        assert assign_problem_letter(25) == "Z"

    def test_double_letters(self):
        """Test double letter assignment (AA-ZZ)."""
        assert assign_problem_letter(26) == "AA"
        assert assign_problem_letter(27) == "AB"
        assert assign_problem_letter(51) == "AZ"
        assert assign_problem_letter(52) == "BA"
        assert assign_problem_letter(701) == "ZZ"

    def test_negative_index_raises_error(self):
        """Test that negative index raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            assign_problem_letter(-1)

    def test_too_large_index_raises_error(self):
        """Test that index > 701 raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            assign_problem_letter(702)

    def test_boundary_conditions(self):
        """Test boundary conditions."""
        # Last single letter
        assert assign_problem_letter(25) == "Z"
        # First double letter
        assert assign_problem_letter(26) == "AA"
        # Last supported letter
        assert assign_problem_letter(701) == "ZZ"


class TestAssignProblemLetters:
    """Tests for assigning letters to multiple problems."""

    def test_assign_letters_to_problems(self):
        """Test assigning letters to a list of problems."""
        # Create mock problem packages
        problems = []
        for i in range(3):
            problem = Mock(spec=ProblemPackage)
            problem.yaml = Mock()
            problem.yaml.name = f"Problem{i}"
            problem.yaml.model_copy = Mock(return_value=Mock())
            problem.ini = Mock()
            problem.ini.model_copy = Mock(return_value=Mock())
            problem.model_copy = Mock(return_value=Mock())
            problems.append(problem)

        # Assign letters
        result = assign_problem_letters(problems)

        # Verify calls were made
        assert len(result) == 3
        assert all(p.yaml.model_copy.called for p in problems)
        assert all(p.ini.model_copy.called for p in problems)

    def test_too_many_problems_raises_error(self):
        """Test that > 702 problems raises ValueError."""
        problems = [Mock(spec=ProblemPackage) for _ in range(703)]

        with pytest.raises(ValueError, match="Too many problems"):
            assign_problem_letters(problems)

    def test_empty_list(self):
        """Test assigning letters to empty list."""
        result = assign_problem_letters([])
        assert result == []

    def test_immutability_preserved(self):
        """Test that original problems are not modified."""
        # Create a mock problem with frozen attributes
        problem = Mock(spec=ProblemPackage)
        problem.yaml = Mock()
        problem.yaml.name = "OriginalName"
        problem.yaml.model_copy = Mock(return_value=Mock(name="A"))
        problem.ini = Mock()
        problem.ini.model_copy = Mock(return_value=Mock())
        problem.model_copy = Mock(return_value=Mock())

        problems = [problem]

        # Assign letters
        assign_problem_letters(problems)

        # Original should still have original name
        assert problem.yaml.name == "OriginalName"
        # model_copy should have been called
        assert problem.yaml.model_copy.called
        assert problem.ini.model_copy.called
        assert problem.model_copy.called
