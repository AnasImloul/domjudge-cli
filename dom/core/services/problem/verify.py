import asyncio
from collections import defaultdict
from tqdm import tqdm

from dom.types.contest import ContestConfig
from dom.types.infra import InfraConfig
from dom.core.services.contest.temp import create_temp_contest
from dom.infrastructure.api.domjudge import DomJudgeAPI
from dom.infrastructure.secrets.manager import load_secret
from dom.core.services.submission.submit import submit_problem

VERDICT = {
    'accepted': 'AC',
    'time_limit_exceeded': 'TLE',
    'runtime_error': 'RTE',
    'wrong_answer': 'WA',
    'memory_limit_exceeded': 'MLE'
}

def verify_problemset(infra: InfraConfig, contest: ContestConfig):
    """
    Verifies a set of contest problems by running submissions and summarizing results.
    """
    client = DomJudgeAPI(
        base_url=f"http://localhost:{infra.port}",
        username="admin",
        password=load_secret("admin_password")
    )

    api_contest, team = create_temp_contest(client, contest)
    results = asyncio.run(_run_submissions(client, api_contest.id, team, contest.problems))

    per_problem, overall_correct, overall_mismatch = _compute_statistics(results)
    _print_per_problem_summary(per_problem)
    _print_overall(overall_correct, overall_mismatch)


async def _run_submissions(client: DomJudgeAPI, contest_id: str, team, problems):
    """
    Submits all problems asynchronously and collects results,
    showing progress with tqdm.
    """
    # 1) schedule submission‐tasks with a progress bar
    tasks = []
    for problem in tqdm(problems, desc="Scheduling submissions", unit="prob"):
        assert problem.id is not None
        problem_tasks = await submit_problem(
            client=client,
            contest_id=contest_id,
            problem=problem,
            team=team
        )
        tasks.extend(problem_tasks)

    # 2) collect results as they complete, with a second bar
    results = []
    for fut in tqdm(asyncio.as_completed(tasks),
                    total=len(tasks),
                    desc="Gathering verdicts",
                    unit="task"):
        judgement, (problem, expected_verdict, file_name) = await fut
        actual = judgement.judgement_type_id or "unknown"
        rt = float(judgement.max_run_time or 0.0)
        results.append((problem, VERDICT.get(expected_verdict), actual, file_name, rt))
    return results


def _compute_statistics(results):
    """
    Aggregates results into per-problem stats and overall counts.
    """
    per_problem = defaultdict(lambda: {
        "correct_runs": [],
        "mismatch_runs": [],
        "correct_count": 0,
        "mismatch_count": 0
    })
    overall_correct = overall_mismatch = 0

    for problem, exp, act, fname, rt in results:
        stats = per_problem[problem.yaml.name]
        if exp == act:
            stats["correct_count"] += 1
            stats["correct_runs"].append(rt)
            overall_correct += 1
        else:
            stats["mismatch_count"] += 1
            stats["mismatch_runs"].append((exp, act, fname, rt))
            overall_mismatch += 1

    return per_problem, overall_correct, overall_mismatch


def _print_per_problem_summary(per_problem):
    print("\n=== Per-Problem Summary ===")
    for name, stats in per_problem.items():
        print(f"- {name}: {stats['correct_count']} correct, {stats['mismatch_count']} mismatches")
        _suggest_tle_to_ac(stats)
        _suggest_ac_to_tle(stats)


def _print_overall(correct: int, mismatch: int):
    print("\n=== Overall ===")
    print(f"Total correct:   {correct}")
    print(f"Total mismatches:{mismatch}")


def _suggest_tle_to_ac(stats):
    """
    For unexpected ACs where expected TLE, suggest tighter timelimit bounds.
    """
    tle_to_ac = [rt for (exp, act, _, rt) in stats["mismatch_runs"] if exp == "TLE" and act == "AC"]
    if not tle_to_ac or not stats["correct_runs"]:
        return
    fastest_unexp = min(tle_to_ac)
    highest_corr = max(stats["correct_runs"])
    lower = 2 * highest_corr
    upper = 0.5 * fastest_unexp

    if lower > upper:
        print(f"  • Warning: lower bound ({lower:.3f}s) exceeds upper ({upper:.3f}s); cannot suggest tight limit.")
    else:
        if upper < 0.5:
            print(f"  • Note: upper bound ({upper:.3f}s) < 0.5s; consider larger testcases.")
        suggested = (lower + upper) / 2
        print(f"  • Suggested timelimit: {suggested:.3f}s ({lower:.3f}s < TL < {upper:.3f}s)")


def _suggest_ac_to_tle(stats):
    """
    For unexpected TLEs where expected AC, suggest raising timelimit.
    """
    ac_to_tle = [rt for (exp, act, _, rt) in stats["mismatch_runs"] if exp == "AC" and act == "TLE"]
    if not ac_to_tle:
        return
    runs = sorted(stats["correct_runs"])
    if not runs:
        print("  • Unexpected TLE: no AC data; consider increasing timelimit.")
        return

    if len(runs) == 1:
        rec = 2 * runs[0]
        print(f"  • Unexpected TLE: raise timelimit to ≥ {rec:.3f}s (2× single AC)")
    else:
        fastest, second, *others = runs
        c1 = 2 * fastest
        c2 = 1.5 * second
        c_others = [1.25 * r for r in others]
        rec = max([c1, c2] + c_others)
        details = [f"2× fastest ({c1:.3f}s)", f"1.5× second ({c2:.3f}s)"]
        details += [f"1.25× {r:.3f}s ({c:.3f}s)" for r, c in zip(others, c_others)]
        print(f"  • Unexpected TLE: raise timelimit to ≥ {rec:.3f}s (max of {', '.join(details)})")
