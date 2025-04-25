# api by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2025-04-25T20:49:24+00:00

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

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
    text: str = Field(..., description='The body of the clarification to send')
    problem_id: Optional[str] = Field(
        None, description='The problem the clarification is for'
    )
    reply_to_id: Optional[str] = Field(
        None, description='The ID of the clarification this clarification is a reply to'
    )
    from_team_id: Optional[str] = Field(
        None,
        description='The team the clarification came from. Only used when adding a clarification as admin',
    )
    to_team_id: Optional[str] = Field(
        None,
        description='The team the clarification must be sent to. Only used when adding a clarification as admin',
    )
    time: Optional[datetime] = Field(
        None,
        description='The time to use for the clarification. Only used when adding a clarification as admin',
    )
    id: Optional[str] = Field(
        None,
        description='The ID to use for the clarification. Only used when adding a clarification as admin and only allowed with PUT',
    )


class PatchContest(BaseModel):
    id: str
    start_time: Optional[str] = Field(
        None, description='The new start time of the contest'
    )
    scoreboard_thaw_time: Optional[str] = Field(
        None, description='The new unfreeze (thaw) time of the contest'
    )
    force: Optional[bool] = Field(
        None,
        description='Force overwriting the start_time even when in next 30s or the scoreboard_thaw_time when already set or too much in the past',
    )


class TeamCategoryPost(BaseModel):
    name: str = Field(..., description='How to name this group on the scoreboard')
    hidden: Optional[bool] = Field(
        None, description='Show this group on the scoreboard?'
    )
    icpc_id: Optional[str] = Field(
        None, description='The ID in the ICPC CMS for this group'
    )
    sortorder: Optional[conint(ge=0)] = Field(
        None,
        description='Bundle groups with the same sortorder, create different scoreboards per sortorder',
    )
    color: Optional[str] = Field(
        None, description='Color to use for teams in this group on the scoreboard'
    )
    allow_self_registration: Optional[bool] = Field(
        None, description='Whether to allow self registration for this group'
    )


class TeamCategoryPut(BaseModel):
    name: str = Field(..., description='How to name this group on the scoreboard')
    hidden: Optional[bool] = Field(
        None, description='Show this group on the scoreboard?'
    )
    icpc_id: Optional[str] = Field(
        None, description='The ID in the ICPC CMS for this group'
    )
    sortorder: Optional[conint(ge=0)] = Field(
        None,
        description='Bundle groups with the same sortorder, create different scoreboards per sortorder',
    )
    color: Optional[str] = Field(
        None, description='Color to use for teams in this group on the scoreboard'
    )
    allow_self_registration: Optional[bool] = Field(
        None, description='Whether to allow self registration for this group'
    )
    id: str = Field(
        ..., description='The ID of the group. Only allowed with PUT requests'
    )


class AddOrganization(BaseModel):
    id: Optional[str] = None
    shortname: Optional[str] = None
    name: Optional[str] = None
    formal_name: Optional[str] = None
    country: Optional[str] = None
    icpc_id: Optional[str] = None


class ContestProblemPut(BaseModel):
    label: str = Field(
        ..., description='The label of the problem to add to the contest'
    )
    color: Optional[str] = Field(
        None,
        description='Human readable color of the problem to add. Will be overwritten by `rgb` if supplied',
    )
    rgb: Optional[str] = Field(
        None,
        description='Hexadecimal RGB value of the color of the problem to add. Overrules `color` if supplied',
    )
    points: Optional[int] = Field(
        None, description='The number of points for the problem to add. Defaults to 1'
    )
    lazy_eval_results: Optional[int] = Field(
        None,
        description='Whether to use lazy evaluation for this problem. Defaults to the global setting',
    )


class AddUser(BaseModel):
    username: str
    name: str
    email: Optional[EmailStr] = None
    ip: Optional[str] = None
    password: Optional[SecretStr] = None
    enabled: Optional[bool] = None
    team_id: Optional[str] = None
    roles: List[str]


class UpdateUser(BaseModel):
    username: str
    name: str
    email: Optional[EmailStr] = None
    ip: Optional[str] = None
    password: Optional[SecretStr] = None
    enabled: Optional[bool] = None
    team_id: Optional[str] = None
    roles: List[str]
    id: str


class User(BaseModel):
    last_login_time: Optional[datetime] = None
    last_api_login_time: Optional[datetime] = None
    first_login_time: Optional[datetime] = None
    team: Optional[str] = None
    team_id: Optional[str] = None
    roles: Optional[List[str]] = Field(
        None, title='Get the roles of this user as an array of strings'
    )
    type: Optional[str] = Field(
        None, title='Get the type of this user for the CCS Specs Contest API'
    )
    id: Optional[str] = None
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    last_ip: Optional[str] = None
    ip: Optional[str] = None
    enabled: Optional[bool] = None


class Award(BaseModel):
    id: Optional[str] = None
    citation: Optional[str] = None
    team_ids: Optional[List[str]] = None


class Clarification(BaseModel):
    time: Optional[str] = None
    contest_time: Optional[str] = None
    problem_id: Optional[str] = None
    reply_to_id: Optional[str] = None
    from_team_id: Optional[str] = None
    to_team_id: Optional[str] = None
    id: Optional[str] = None
    externalid: Optional[str] = None
    text: Optional[str] = None
    answered: Optional[bool] = None


class ContestState(BaseModel):
    started: Optional[str] = None
    ended: Optional[str] = None
    frozen: Optional[str] = None
    thawed: Optional[str] = None
    finalized: Optional[str] = None
    end_of_updates: Optional[str] = None


class ContestStatus(BaseModel):
    num_submissions: Optional[int] = None
    num_queued: Optional[int] = None
    num_judging: Optional[int] = None


class ApiVersion(BaseModel):
    api_version: Optional[int] = None


class ExtendedContestStatus(BaseModel):
    cid: Optional[str] = None
    num_submissions: Optional[int] = None
    num_queued: Optional[int] = None
    num_judging: Optional[int] = None


class TeamCategory(BaseModel):
    hidden: Optional[bool] = None
    id: Optional[str] = None
    icpc_id: Optional[str] = None
    name: str
    sortorder: Optional[conint(ge=0)] = None
    color: Optional[str] = None
    allow_self_registration: Optional[bool] = None


class Judgehost(BaseModel):
    id: Optional[str] = None
    hostname: Optional[constr(pattern=r'[A-Za-z0-9_\-.]*')] = None
    enabled: Optional[bool] = None
    polltime: Optional[str] = None
    hidden: Optional[bool] = None


class JudgehostFile(BaseModel):
    filename: Optional[str] = None
    content: Optional[str] = None
    is_executable: Optional[bool] = None


class JudgeTask(BaseModel):
    submitid: Optional[str] = None
    judgetaskid: Optional[int] = None
    type: Optional[str] = None
    priority: Optional[int] = None
    jobid: Optional[str] = None
    uuid: Optional[str] = None
    compile_script_id: Optional[str] = None
    run_script_id: Optional[str] = None
    compare_script_id: Optional[str] = None
    testcase_id: Optional[str] = None
    testcase_hash: Optional[str] = None
    compile_config: Optional[str] = None
    run_config: Optional[str] = None
    compare_config: Optional[str] = None


class JudgingWrapper(BaseModel):
    max_run_time: Optional[float] = None
    start_time: Optional[str] = None
    start_contest_time: Optional[str] = None
    end_time: Optional[str] = None
    end_contest_time: Optional[str] = None
    submission_id: Optional[str] = None
    id: Optional[str] = None
    valid: Optional[bool] = None
    judgement_type_id: Optional[str] = None


class JudgementType(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    penalty: Optional[bool] = None
    solved: Optional[bool] = None


class JudgingRunWrapper(BaseModel):
    run_time: Optional[float] = None
    time: Optional[str] = None
    contest_time: Optional[str] = None
    judgement_id: Optional[str] = None
    ordinal: Optional[int] = None
    id: Optional[str] = None
    judgement_type_id: Optional[str] = None


class SourceCode(BaseModel):
    id: Optional[str] = None
    submission_id: Optional[str] = None
    filename: Optional[str] = None
    source: Optional[str] = None


class AddSubmissionFile(BaseModel):
    data: Optional[str] = Field(None, description='The base64 encoded submission files')
    mime: Optional[str] = Field(
        None, description='The mime type of the file. Should be application/zip'
    )


class AddTeamLocation(BaseModel):
    description: Optional[str] = None


class AccessEndpoint(BaseModel):
    type: Optional[str] = None
    properties: Optional[List[str]] = None


class ImageFile(BaseModel):
    href: Optional[str] = None
    mime: Optional[str] = None
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class FileWithName(BaseModel):
    href: Optional[str] = None
    mime: Optional[str] = None
    filename: Optional[str] = None


class ApiInfoProvider(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    build_date: Optional[str] = None


class DomJudgeApiInfo(BaseModel):
    apiversion: Optional[int] = None
    version: Optional[str] = None
    environment: Optional[str] = None
    doc_url: Optional[str] = None


class Command(BaseModel):
    version: Optional[str] = None
    version_command: Optional[str] = None


class TeamLocation(BaseModel):
    description: Optional[str] = None


class Score(BaseModel):
    num_solved: Optional[int] = None
    total_time: Optional[int] = None
    total_runtime: Optional[int] = None


class Problem(BaseModel):
    label: Optional[str] = None
    problem_id: Optional[str] = None
    num_judged: Optional[int] = None
    num_pending: Optional[int] = None
    solved: Optional[bool] = None
    time: Optional[int] = None
    first_to_solve: Optional[bool] = None
    runtime: Optional[int] = None
    fastest_submission: Optional[bool] = None


class AddSubmission(BaseModel):
    problem: Optional[str] = Field(
        None, description='The problem to submit a solution for'
    )
    problem_id: Optional[str] = Field(
        None, description='The problem to submit a solution for'
    )
    language: Optional[str] = Field(
        None, description='The language to submit a solution in'
    )
    language_id: Optional[str] = Field(
        None, description='The language to submit a solution in'
    )
    team_id: Optional[str] = Field(
        None,
        description='The team to submit a solution for. Only used when adding a submission as admin',
    )
    user_id: Optional[str] = Field(
        None,
        description='The user to submit a solution for. Only used when adding a submission as admin',
    )
    time: Optional[datetime] = Field(
        None,
        description='The time to use for the submission. Only used when adding a submission as admin',
    )
    entry_point: Optional[str] = Field(
        None,
        description='The entry point for the submission. Required for languages requiring an entry point',
    )
    id: Optional[str] = Field(
        None,
        description='The ID to use for the submission. Only used when adding a submission as admin and only allowed with PUT',
    )
    files: Optional[List[AddSubmissionFile]] = Field(
        None,
        description='The base64 encoded ZIP file to submit',
        max_items=1,
        min_items=1,
    )
    code: Optional[List[bytes]] = Field(None, description='The file(s) to submit')


class AddTeam(BaseModel):
    id: Optional[str] = None
    icpc_id: Optional[str] = None
    label: Optional[str] = None
    group_ids: Optional[List[str]] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    public_description: Optional[str] = None
    members: Optional[str] = None
    description: Optional[str] = None
    location: Optional[AddTeamLocation] = None
    organization_id: Optional[str] = None


class Access(BaseModel):
    capabilities: Optional[List[str]] = None
    endpoints: Optional[List[AccessEndpoint]] = None


class Contest(BaseModel):
    formal_name: Optional[str] = None
    scoreboard_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    scoreboard_thaw_time: Optional[datetime] = None
    duration: Optional[str] = None
    scoreboard_freeze_duration: Optional[str] = None
    banner: Optional[List[ImageFile]] = None
    problemset: Optional[List[FileWithName]] = None
    id: Optional[str] = None
    external_id: Optional[str] = None
    name: str
    shortname: str
    allow_submit: Optional[bool] = None
    runtime_as_score_tiebreaker: Optional[bool] = None
    warning_message: Optional[str] = None
    penalty_time: Optional[int] = None


class ApiInfo(BaseModel):
    version: Optional[str] = None
    version_url: Optional[str] = None
    name: Optional[str] = None
    provider: Optional[ApiInfoProvider] = None
    domjudge: Optional[DomJudgeApiInfo] = None


class Language(BaseModel):
    compile_executable_hash: Optional[str] = None
    compiler: Optional[Command] = None
    runner: Optional[Command] = None
    id: Optional[str] = None
    name: str
    extensions: List[str]
    filter_compiler_files: Optional[bool] = None
    allow_judge: Optional[bool] = None
    time_factor: PositiveFloat
    entry_point_required: Optional[bool] = None
    entry_point_name: Optional[str] = None


class TeamAffiliation(BaseModel):
    shortname: Optional[str] = None
    logo: Optional[List[ImageFile]] = None
    id: Optional[str] = None
    icpc_id: Optional[str] = None
    name: str
    formal_name: str
    country: Optional[str] = None
    country_flag: Optional[List[ImageFile]] = Field(
        None,
        title='This field gets filled by the team affiliation visitor with a data transfer\nobject that represents the country flag',
    )


class ContestProblem(BaseModel):
    id: Optional[str] = None
    short_name: Optional[str] = None
    rgb: Optional[str] = None
    color: Optional[str] = None
    label: str
    time_limit: Optional[PositiveFloat] = None
    statement: Optional[List[FileWithName]] = None
    externalid: Optional[str] = None
    name: str


class Submission(BaseModel):
    language_id: Optional[str] = None
    time: Optional[str] = None
    contest_time: Optional[str] = None
    team_id: Optional[str] = None
    problem_id: Optional[str] = None
    files: Optional[List[FileWithName]] = None
    id: Optional[str] = None
    external_id: Optional[str] = None
    entry_point: Optional[str] = None
    import_error: Optional[str] = None


class Team(BaseModel):
    location: Optional[TeamLocation] = None
    organization_id: Optional[str] = None
    hidden: Optional[bool] = None
    group_ids: Optional[List[str]] = None
    affiliation: Optional[str] = None
    nationality: Optional[str] = None
    photo: Optional[List[ImageFile]] = None
    id: Optional[str] = None
    icpc_id: Optional[str] = None
    label: Optional[str] = None
    name: str
    display_name: Optional[str] = None
    public_description: Optional[str] = None


class Row(BaseModel):
    rank: Optional[int] = None
    team_id: Optional[str] = None
    score: Optional[Score] = None
    problems: Optional[List[Problem]] = None


class Balloon(BaseModel):
    balloonid: Optional[int] = None
    time: Optional[str] = None
    problem: Optional[str] = None
    contestproblem: Optional[ContestProblem] = None
    team: Optional[str] = None
    teamid: Optional[int] = None
    location: Optional[str] = None
    affiliation: Optional[str] = None
    affiliationid: Optional[int] = None
    category: Optional[str] = None
    categoryid: Optional[int] = None
    total: Optional[Dict[str, ContestProblem]] = None
    awards: Optional[str] = None
    done: Optional[bool] = None


class Scoreboard(BaseModel):
    event_id: Optional[str] = None
    time: Optional[str] = None
    contest_time: Optional[str] = None
    state: Optional[ContestState] = None
    rows: Optional[List[Row]] = None
