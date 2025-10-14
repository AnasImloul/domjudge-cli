# api by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2025-04-25T20:49:24+00:00

from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    PositiveFloat,
    SecretStr,
    conint,
    constr,
)


class ClarificationPost(BaseModel):
    text: str = Field(..., description="The body of the clarification to send")
    problem_id: str | None = Field(None, description="The problem the clarification is for")
    reply_to_id: str | None = Field(None, description="The ID of the clarification this clarification is a reply to")
    from_team_id: str | None = Field(
        None,
        description="The team the clarification came from. Only used when adding a clarification as admin",
    )
    to_team_id: str | None = Field(
        None,
        description="The team the clarification must be sent to. Only used when adding a clarification as admin",
    )
    time: datetime | None = Field(
        None,
        description="The time to use for the clarification. Only used when adding a clarification as admin",
    )
    id: str | None = Field(
        None,
        description="The ID to use for the clarification. Only used when adding a clarification as admin and only allowed with PUT",
    )


class PatchContest(BaseModel):
    id: str
    start_time: str | None = Field(None, description="The new start time of the contest")
    scoreboard_thaw_time: str | None = Field(None, description="The new unfreeze (thaw) time of the contest")
    force: bool | None = Field(
        None,
        description="Force overwriting the start_time even when in next 30s or the scoreboard_thaw_time when already set or too much in the past",
    )


class TeamCategoryPost(BaseModel):
    name: str = Field(..., description="How to name this group on the scoreboard")
    hidden: bool | None = Field(None, description="Show this group on the scoreboard?")
    icpc_id: str | None = Field(None, description="The ID in the ICPC CMS for this group")
    sortorder: conint(ge=0) | None = Field(  # type: ignore[valid-type]
        None,
        description="Bundle groups with the same sortorder, create different scoreboards per sortorder",
    )
    color: str | None = Field(None, description="Color to use for teams in this group on the scoreboard")
    allow_self_registration: bool | None = Field(None, description="Whether to allow self registration for this group")


class TeamCategoryPut(BaseModel):
    name: str = Field(..., description="How to name this group on the scoreboard")
    hidden: bool | None = Field(None, description="Show this group on the scoreboard?")
    icpc_id: str | None = Field(None, description="The ID in the ICPC CMS for this group")
    sortorder: conint(ge=0) | None = Field(  # type: ignore[valid-type]
        None,
        description="Bundle groups with the same sortorder, create different scoreboards per sortorder",
    )
    color: str | None = Field(None, description="Color to use for teams in this group on the scoreboard")
    allow_self_registration: bool | None = Field(None, description="Whether to allow self registration for this group")
    id: str = Field(..., description="The ID of the group. Only allowed with PUT requests")


class AddOrganization(BaseModel):
    id: str | None = None
    shortname: str | None = None
    name: str | None = None
    formal_name: str | None = None
    country: str | None = None
    icpc_id: str | None = None


class ContestProblemPut(BaseModel):
    label: str = Field(..., description="The label of the problem to add to the contest")
    color: str | None = Field(
        None,
        description="Human readable color of the problem to add. Will be overwritten by `rgb` if supplied",
    )
    rgb: str | None = Field(
        None,
        description="Hexadecimal RGB value of the color of the problem to add. Overrules `color` if supplied",
    )
    points: int | None = Field(None, description="The number of points for the problem to add. Defaults to 1")
    lazy_eval_results: int | None = Field(
        None,
        description="Whether to use lazy evaluation for this problem. Defaults to the global setting",
    )


class AddUser(BaseModel):
    username: str
    name: str
    email: EmailStr | None = None
    ip: str | None = None
    password: SecretStr | None = None
    enabled: bool | None = None
    team_id: str | None = None
    roles: list[str]


class UpdateUser(BaseModel):
    username: str
    name: str
    email: EmailStr | None = None
    ip: str | None = None
    password: SecretStr | None = None
    enabled: bool | None = None
    team_id: str | None = None
    roles: list[str]
    id: str


class User(BaseModel):
    last_login_time: datetime | None = None
    last_api_login_time: datetime | None = None
    first_login_time: datetime | None = None
    team: str | None = None
    team_id: str | None = None
    roles: list[str] | None = Field(None, title="Get the roles of this user as an array of strings")
    type: str | None = Field(None, title="Get the type of this user for the CCS Specs Contest API")
    id: str | None = None
    username: str
    name: str | None = None
    email: str | None = None
    last_ip: str | None = None
    ip: str | None = None
    enabled: bool | None = None


class Award(BaseModel):
    id: str | None = None
    citation: str | None = None
    team_ids: list[str] | None = None


class Clarification(BaseModel):
    time: str | None = None
    contest_time: str | None = None
    problem_id: str | None = None
    reply_to_id: str | None = None
    from_team_id: str | None = None
    to_team_id: str | None = None
    id: str | None = None
    externalid: str | None = None
    text: str | None = None
    answered: bool | None = None


class ContestState(BaseModel):
    started: str | None = None
    ended: str | None = None
    frozen: str | None = None
    thawed: str | None = None
    finalized: str | None = None
    end_of_updates: str | None = None


class ContestStatus(BaseModel):
    num_submissions: int | None = None
    num_queued: int | None = None
    num_judging: int | None = None


class ApiVersion(BaseModel):
    api_version: int | None = None


class ExtendedContestStatus(BaseModel):
    cid: str | None = None
    num_submissions: int | None = None
    num_queued: int | None = None
    num_judging: int | None = None


class TeamCategory(BaseModel):
    hidden: bool | None = None
    id: str | None = None
    icpc_id: str | None = None
    name: str
    sortorder: conint(ge=0) | None = None  # type: ignore[valid-type]
    color: str | None = None
    allow_self_registration: bool | None = None


class Judgehost(BaseModel):
    id: str | None = None
    hostname: constr(pattern=r"[A-Za-z0-9_\-.]*") | None = None  # type: ignore[valid-type]
    enabled: bool | None = None
    polltime: str | None = None
    hidden: bool | None = None


class JudgehostFile(BaseModel):
    filename: str | None = None
    content: str | None = None
    is_executable: bool | None = None


class JudgeTask(BaseModel):
    submitid: str | None = None
    judgetaskid: int | None = None
    type: str | None = None
    priority: int | None = None
    jobid: str | None = None
    uuid: str | None = None
    compile_script_id: str | None = None
    run_script_id: str | None = None
    compare_script_id: str | None = None
    testcase_id: str | None = None
    testcase_hash: str | None = None
    compile_config: str | None = None
    run_config: str | None = None
    compare_config: str | None = None


class JudgingWrapper(BaseModel):
    max_run_time: float | None = None
    start_time: str | None = None
    start_contest_time: str | None = None
    end_time: str | None = None
    end_contest_time: str | None = None
    submission_id: str | None = None
    id: str | None = None
    valid: bool | None = None
    judgement_type_id: str | None = None


class JudgementType(BaseModel):
    id: str | None = None
    name: str | None = None
    penalty: bool | None = None
    solved: bool | None = None


class JudgingRunWrapper(BaseModel):
    run_time: float | None = None
    time: str | None = None
    contest_time: str | None = None
    judgement_id: str | None = None
    ordinal: int | None = None
    id: str | None = None
    judgement_type_id: str | None = None


class SourceCode(BaseModel):
    id: str | None = None
    submission_id: str | None = None
    filename: str | None = None
    source: str | None = None


class AddSubmissionFile(BaseModel):
    data: str | None = Field(None, description="The base64 encoded submission files")
    mime: str | None = Field(None, description="The mime type of the file. Should be application/zip")


class AddTeamLocation(BaseModel):
    description: str | None = None


class AccessEndpoint(BaseModel):
    type: str | None = None
    properties: list[str] | None = None


class ImageFile(BaseModel):
    href: str | None = None
    mime: str | None = None
    filename: str | None = None
    width: int | None = None
    height: int | None = None


class FileWithName(BaseModel):
    href: str | None = None
    mime: str | None = None
    filename: str | None = None


class ApiInfoProvider(BaseModel):
    name: str | None = None
    version: str | None = None
    build_date: str | None = None


class DomJudgeApiInfo(BaseModel):
    apiversion: int | None = None
    version: str | None = None
    environment: str | None = None
    doc_url: str | None = None


class Command(BaseModel):
    version: str | None = None
    version_command: str | None = None


class TeamLocation(BaseModel):
    description: str | None = None


class Score(BaseModel):
    num_solved: int | None = None
    total_time: int | None = None
    total_runtime: int | None = None


class Problem(BaseModel):
    label: str | None = None
    problem_id: str | None = None
    num_judged: int | None = None
    num_pending: int | None = None
    solved: bool | None = None
    time: int | None = None
    first_to_solve: bool | None = None
    runtime: int | None = None
    fastest_submission: bool | None = None


class AddSubmission(BaseModel):
    problem: str | None = Field(None, description="The problem to submit a solution for")
    problem_id: str | None = Field(None, description="The problem to submit a solution for")
    language: str | None = Field(None, description="The language to submit a solution in")
    language_id: str | None = Field(None, description="The language to submit a solution in")
    team_id: str | None = Field(
        None,
        description="The team to submit a solution for. Only used when adding a submission as admin",
    )
    user_id: str | None = Field(
        None,
        description="The user to submit a solution for. Only used when adding a submission as admin",
    )
    time: datetime | None = Field(
        None,
        description="The time to use for the submission. Only used when adding a submission as admin",
    )
    entry_point: str | None = Field(
        None,
        description="The entry point for the submission. Required for languages requiring an entry point",
    )
    id: str | None = Field(
        None,
        description="The ID to use for the submission. Only used when adding a submission as admin and only allowed with PUT",
    )
    files: list[AddSubmissionFile] | None = Field(  # type: ignore[call-overload]
        None,
        description="The base64 encoded ZIP file to submit",
        max_items=1,
        min_items=1,
    )
    code: list[bytes] | None = Field(None, description="The file(s) to submit")


class AddTeam(BaseModel):
    id: str | None = None
    icpc_id: str | None = None
    label: str | None = None
    group_ids: list[str] | None = None
    name: str | None = None
    display_name: str | None = None
    public_description: str | None = None
    members: str | None = None
    description: str | None = None
    location: AddTeamLocation | None = None
    organization_id: str | None = None


class Access(BaseModel):
    capabilities: list[str] | None = None
    endpoints: list[AccessEndpoint] | None = None


class Contest(BaseModel):
    formal_name: str | None = None
    scoreboard_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    scoreboard_thaw_time: datetime | None = None
    duration: str | None = None
    scoreboard_freeze_duration: str | None = None
    banner: list[ImageFile] | None = None
    problemset: list[FileWithName] | None = None
    id: str | None = None
    external_id: str | None = None
    name: str
    shortname: str
    allow_submit: bool | None = None
    runtime_as_score_tiebreaker: bool | None = None
    warning_message: str | None = None
    penalty_time: int | None = None


class ApiInfo(BaseModel):
    version: str | None = None
    version_url: str | None = None
    name: str | None = None
    provider: ApiInfoProvider | None = None
    domjudge: DomJudgeApiInfo | None = None


class Language(BaseModel):
    compile_executable_hash: str | None = None
    compiler: Command | None = None
    runner: Command | None = None
    id: str | None = None
    name: str
    extensions: list[str]
    filter_compiler_files: bool | None = None
    allow_judge: bool | None = None
    time_factor: PositiveFloat
    entry_point_required: bool | None = None
    entry_point_name: str | None = None


class TeamAffiliation(BaseModel):
    shortname: str | None = None
    logo: list[ImageFile] | None = None
    id: str | None = None
    icpc_id: str | None = None
    name: str
    formal_name: str
    country: str | None = None
    country_flag: list[ImageFile] | None = Field(
        None,
        title="This field gets filled by the team affiliation visitor with a data transfer\nobject that represents the country flag",
    )


class ContestProblem(BaseModel):
    id: str | None = None
    short_name: str | None = None
    rgb: str | None = None
    color: str | None = None
    label: str
    time_limit: PositiveFloat | None = None
    statement: list[FileWithName] | None = None
    externalid: str | None = None
    name: str


class Submission(BaseModel):
    language_id: str | None = None
    time: str | None = None
    contest_time: str | None = None
    team_id: str | None = None
    problem_id: str | None = None
    files: list[FileWithName] | None = None
    id: str | None = None
    external_id: str | None = None
    entry_point: str | None = None
    import_error: str | None = None


class Team(BaseModel):
    location: TeamLocation | None = None
    organization_id: str | None = None
    hidden: bool | None = None
    group_ids: list[str] | None = None
    affiliation: str | None = None
    nationality: str | None = None
    photo: list[ImageFile] | None = None
    id: str | None = None
    icpc_id: str | None = None
    label: str | None = None
    name: str
    display_name: str | None = None
    public_description: str | None = None


class Row(BaseModel):
    rank: int | None = None
    team_id: str | None = None
    score: Score | None = None
    problems: list[Problem] | None = None


class Balloon(BaseModel):
    balloonid: int | None = None
    time: str | None = None
    problem: str | None = None
    contestproblem: ContestProblem | None = None
    team: str | None = None
    teamid: int | None = None
    location: str | None = None
    affiliation: str | None = None
    affiliationid: int | None = None
    category: str | None = None
    categoryid: int | None = None
    total: dict[str, ContestProblem] | None = None
    awards: str | None = None
    done: bool | None = None


class Scoreboard(BaseModel):
    event_id: str | None = None
    time: str | None = None
    contest_time: str | None = None
    state: ContestState | None = None
    rows: list[Row] | None = None
