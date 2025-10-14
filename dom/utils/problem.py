"""Problem-related utility functions."""

from dom.logging_config import get_logger
from dom.types.problem import ProblemPackage

logger = get_logger(__name__)


def assign_problem_letter(index: int) -> str:
    """
    Assign a problem letter identifier based on index.

    Supports up to 702 problems (A-Z, AA-ZZ).

    Args:
        index: 0-based problem index

    Returns:
        Problem letter identifier (A, B, ..., Z, AA, AB, ..., ZZ)

    Raises:
        ValueError: If index is negative or > 701

    Examples:
        >>> assign_problem_letter(0)
        'A'
        >>> assign_problem_letter(25)
        'Z'
        >>> assign_problem_letter(26)
        'AA'
        >>> assign_problem_letter(27)
        'AB'
    """
    if index < 0:
        raise ValueError(f"Problem index must be non-negative, got {index}")

    # Single letter (A-Z): 0-25
    if index < 26:
        return chr(ord("A") + index)

    # Double letter (AA-ZZ): 26-701
    if index < 702:  # 26 + (26 * 26)
        adjusted_index = index - 26
        first = chr(ord("A") + (adjusted_index // 26))
        second = chr(ord("A") + (adjusted_index % 26))
        return f"{first}{second}"

    # If someone has > 702 problems in a contest, we have bigger issues
    raise ValueError(f"Problem index {index} too large. Maximum 702 problems supported (A-ZZ).")


def assign_problem_letters(problems: list[ProblemPackage]) -> list[ProblemPackage]:
    """
    Assign problem letters (A, B, C, ...) to a list of problem packages.

    This creates new problem package instances with updated identifiers,
    preserving immutability of the original objects.

    Args:
        problems: List of problem packages

    Returns:
        New list of problem packages with assigned letters

    Raises:
        ValueError: If too many problems (>702)
    """
    if len(problems) > 702:
        raise ValueError(f"Too many problems: {len(problems)}. Maximum 702 supported (A-ZZ).")

    updated_problems = []

    for i, problem in enumerate(problems):
        letter = assign_problem_letter(i)

        # Create new objects instead of mutating (respecting immutability)
        updated_yaml = problem.yaml.model_copy(update={"name": letter})
        updated_ini = problem.ini.model_copy(update={"externalid": letter, "short_name": letter})

        # Create new problem package with updated configs
        updated_problem = problem.model_copy(update={"yaml": updated_yaml, "ini": updated_ini})

        updated_problems.append(updated_problem)

        logger.debug(
            f"Assigned letter '{letter}' to problem",
            extra={
                "problem_index": i,
                "problem_letter": letter,
                "original_name": problem.yaml.name,
            },
        )

    return updated_problems
