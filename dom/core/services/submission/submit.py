import asyncio
import re
from pathlib import Path

from dom.infrastructure.api import DomJudgeAPI
from dom.types.api.models import JudgingWrapper
from dom.types.problem import ProblemPackage
from dom.types.team import Team

# Mapping from file extension to language
EXTENSION_TO_LANGUAGE = {
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c++": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".h++": "cpp",
    ".java": "java",
    ".py": "python3",
    ".js": "javascript",
    ".rs": "rust",
    ".go": "golang",
}


def modify_source_code(file_name: str, code_bytes: bytes, language: str) -> tuple[str, bytes]:
    code_str = code_bytes.decode("utf-8")
    if language == "cpp":
        if "#include <bits/stdc++.h>" not in code_str:
            code_str = "#include <bits/stdc++.h>\n" + code_str
        return file_name, code_str.encode("utf-8")

    if language == "java":
        match = re.search(r"\bpublic\s+class\s+(\w+)", code_str)
        if not match:
            raise ValueError(f"Could not find public class in Java file {file_name}")
        class_name = match.group(1)
        new_file_name = f"{class_name}.java"
        code_str = re.sub(r"\bpublic\s+class\s+\w+", f"public class {class_name}", code_str)
        return new_file_name, code_str.encode("utf-8")

    return file_name, code_bytes


async def submit_problem(
    client: DomJudgeAPI,
    contest_id: str,
    problem: ProblemPackage,
    team: Team,
    poll_interval: float = 1.0,
) -> list[asyncio.Task[tuple[JudgingWrapper, tuple[ProblemPackage, str, str]]]]:
    """
    Submits all verdict-related files for `problem` and returns a list of Tasks.
    Each Task yields the final judgement when awaited.
    """
    loop = asyncio.get_running_loop()

    verdicts = {
        "accepted": problem.submissions.accepted,
        "time_limit_exceeded": problem.submissions.time_limit_exceeded,
        "wrong_answer": problem.submissions.wrong_answer,
    }

    async def _handle_one(verdict: str, file_name: str, source_bytes: bytes):
        ext = Path(file_name).suffix
        language = EXTENSION_TO_LANGUAGE.get(ext.lower())
        if language is None:
            raise ValueError(f"Unsupported file extension: {ext} in file {file_name}")

        # rewrite if needed
        modified_name, modified_bytes = modify_source_code(file_name, source_bytes, language)

        # Ensure problem has an ID (type narrowing for mypy)
        if not problem.id:
            raise ValueError(f"Problem {problem.yaml.name} has no ID assigned")
        problem_id: str = problem.id  # Now we know it's not None

        # send submission off to the default executor
        submission = await loop.run_in_executor(
            None,
            lambda: client.submissions.submit(
                contest_id,
                problem_id,  # Properly typed as str
                modified_name,
                language,
                modified_bytes,
                team,
            ),
        )

        # Ensure submission has an ID (type narrowing for mypy)
        if not submission.id:
            raise ValueError(f"Submission for {file_name} has no ID in response")
        submission_id: str = submission.id  # Now we know it's not None

        # poll until a judgement arrives
        while True:
            judgement = await loop.run_in_executor(
                None,
                lambda: client.submissions.get_judgement(
                    contest_id, submission_id
                ),  # Properly typed as str
            )
            if judgement is not None and judgement.judgement_type_id is not None:
                return judgement, (problem, verdict, file_name)
            await asyncio.sleep(poll_interval)

    # kick off one task per file
    tasks: list[asyncio.Task] = []
    for verdict, submissions in verdicts.items():
        for fname, fbytes in submissions.items():
            tasks.append(asyncio.create_task(_handle_one(verdict, fname, fbytes)))

    return tasks
