import requests
import os
from requests.auth import HTTPBasicAuth
import json
import tempfile
from pathlib import Path

from dom.types.problem import ProblemPackage
from dom.types.team import Team
from dom.types.api import models
from io import BytesIO


class DomJudgeAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_user(self, user_id: int) -> models.User:
        response = self.session.get(self._url(f"/api/v4/users/{user_id}/"))
        response.raise_for_status()
        return models.User(**response.json())

    def list_contests(self) -> list:
        response = self.session.get(self._url("/api/v4/contests"))
        response.raise_for_status()
        return response.json()

    def create_contest(self, contest_data: models.Contest) -> tuple[str, bool]:
        contest_json = contest_data.model_dump_json()
        file_like = BytesIO(contest_json.encode('utf-8'))
        files = {
            'json': ('contest.json', file_like, 'application/json')
        }
        try:
            response = self.session.post(self._url("/api/v4/contests"), files=files)
            response.raise_for_status()
            print(f"[INFO] Created new contest with shortname '{contest_data.shortname}'.")
            contest_id = response.json()
            contest_data.id = contest_id
            return contest_id, True

        except requests.HTTPError as http_err:
            if response.status_code == 400:
                try:
                    error_detail = response.json()
                    error_message = error_detail.get('message', '')
                except Exception:
                    error_message = response.text

                if "shortname" in error_message:
                    existing_contests = self.list_contests()
                    for contest in existing_contests:
                        if contest.get("shortname") == contest_data.shortname:
                            print(f"[INFO] Contest '{contest_data.shortname}' already exists.")
                            contest_data.id = contest["id"]
                            return contest["id"], False
                    print(f"[ERROR] Contest with shortname '{contest_data.shortname}' not found after 400 error.")
                    raise Exception(f"Contest with shortname '{contest_data.shortname}' exists but could not fetch it.")

            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            raise

    def list_contest_problems(self, contest_id: str):
        response = self.session.get(self._url(f"/api/v4/contests/{contest_id}/problems"))
        response.raise_for_status()
        return response.json()

    def list_all_problems(self) -> dict:
        all_problems = {}
        contests = self.list_contests()
        for contest in contests:
            contest_id = contest["id"]
            problems = self.list_contest_problems(contest_id)
            for problem in problems:
                externalid = problem.get("externalid")
                if externalid and externalid not in all_problems:
                    all_problems[externalid] = problem
        return all_problems

    def create_or_get_problem(self, problem_package: ProblemPackage) -> str:
        all_problems = self.list_all_problems()

        externalid = problem_package.ini.externalid

        if externalid in all_problems:
            problem_id = all_problems[externalid]["id"]
            print(f"[INFO] Problem with externalid '{externalid}' already exists globally.")
        else:
            temp_zip_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                    temp_zip_path = temp_zip.name
                    problem_package.write_to_zip(Path(temp_zip_path))

                with open(temp_zip_path, 'rb') as f:
                    files = {
                        'zip': (f.name, f, 'application/zip')
                    }
                    response = self.session.post(self._url("/api/v4/problems"), files=files)
                    response.raise_for_status()

                    resp_json = response.json()
                    if "problem_id" not in resp_json:
                        raise Exception(f"[ERROR] No 'problem_id' in problem creation response: {resp_json}")

                    problem_id = resp_json["problem_id"]
                    print(f"[INFO] Created new problem with ID {problem_id}.")
            finally:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)

        return problem_id

    def add_problem_to_contest(self, contest_id: str, problem_package: ProblemPackage) -> str:
        problem_id = self.create_or_get_problem(problem_package)
        if problem_id in map(lambda problem: problem["id"], self.list_contest_problems(contest_id)):
            print(f"[INFO] Problem already linked to contest")
            return problem_id

        put_response = self.session.put(
            self._url(f"/api/v4/contests/{contest_id}/problems/{problem_id}"),
            json={
                "label": problem_package.yaml.name,
                "color": problem_package.ini.color
            }
        )
        put_response.raise_for_status()
        print(f"[INFO] Linked problem ID {problem_id} to contest {contest_id}.")

        return problem_id

    def list_contest_teams(self, contest_id: str):
        response = self.session.get(self._url(f"/api/v4/contests/{contest_id}/teams"))
        response.raise_for_status()
        return response.json()

    def list_users(self):
        response = self.session.get(self._url(f"/api/v4/users"))
        response.raise_for_status()
        return response.json()

    def add_team_to_contest(self, contest_id: str, team_data: models.AddTeam) -> tuple[str, bool]:
        for team in self.list_contest_teams(contest_id):
            if team["name"] == team_data.name:
                print(f"[INFO] Team with name '{team_data.name}' already exists for this contest_id {contest_id}.")
                return team["id"], True

        data = json.loads(team_data.model_dump_json(exclude_unset=True))
        response = self.session.post(
            url=self._url(f"/api/v4/contests/{contest_id}/teams"),
            json=data,
        )
        response.raise_for_status()
        resp_json = response.json()
        if "id" not in resp_json:
            raise Exception(f"[ERROR] No 'id' in team creation response: {resp_json}")

        team_id = resp_json["id"]
        print(f"[INFO] Created new team for contest {contest_id} with name '{team_data.name}'.")
        return team_id, False

    def add_user(self, user_data: models.AddUser) -> str:
        for user in self.list_users():
            if user["name"] == user_data.username:
                print(f"[INFO] User with name '{user_data.username}' already exists.")
                return user["id"]

        data = json.loads(user_data.model_dump_json(exclude_unset=True))
        data["password"] = user_data.password.get_secret_value()
        response = self.session.post(
            url=self._url(f"/api/v4/users"),
            json=data,
        )
        response.raise_for_status()
        print(f"[INFO] Created new user with name '{user_data.username}'.")
        return response.json()

    def send_submission(self, contest_id: str, problem_id: str, file_name: str, language: str, source_code: bytes, team: Team):
        url = self._url(f"/api/v4/contests/{contest_id}/submissions")
        auth = HTTPBasicAuth(team.name, team.password.get_secret_value())

        # Create a temp file to hold the source code
        with tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix=os.path.splitext(file_name)[1]) as tmp_file:
            tmp_file.write(source_code)
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, 'rb') as code_file:
                files = {
                    'code': (file_name, code_file, 'text/x-source-code')
                }
                data = {
                    'problem': problem_id,
                    'language': language,
                    'team': team.id
                }
                response = requests.post(url, data=data, files=files, auth=auth)
                response.raise_for_status()
                print(f"[INFO] Submitted '{file_name}' to contest {contest_id} for team {team.name}.")
                return models.Submission(**response.json())

        except requests.HTTPError as e:
            print(f"[ERROR] Submission failed for '{file_name}': {e.response.text}")
            raise

        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    def get_submission_judgement(self, contest_id: str, submission_id: str):
        response = self.session.get(self._url(f"/api/v4/contests/{contest_id}/judgements?submission_id={submission_id}&strict=false"))
        response.raise_for_status()
        judgements = response.json()
        if len(judgements) == 0:
            return None
        return models.JudgingWrapper(**judgements[0])

    def add_organization(self, contest_id: str, organization: models.AddOrganization) -> tuple[str, bool]:
        """
        Add an organization to the given contest.
        Returns a tuple (organization_id, already_exists).
        already_exists == True if the org was already linked to the contest.
        """
        # 1. List existing organizations on this contest
        list_resp = self.session.get(self._url(f"/api/v4/contests/{contest_id}/organizations"))
        list_resp.raise_for_status()
        existing_orgs = list_resp.json()

        # 2. Check if this organization is already present
        for org in existing_orgs:
            if org.get("name") == organization.name:
                print(f"[INFO] Organization '{organization.name}' already exists in contest {contest_id}.")
                return organization.id or org["id"], True

        # 3. Not present: create it
        payload = json.loads(organization.model_dump_json(exclude_unset=True))
        post_resp = self.session.post(
            self._url(f"/api/v4/contests/{contest_id}/organizations"),
            json=payload
        )
        post_resp.raise_for_status()
        resp_json = post_resp.json()
        if "id" not in resp_json:
            raise Exception(f"[ERROR] No 'id' in organization creation response: {resp_json}")

        org_id = resp_json["id"]
        print(f"[INFO] Created new organization '{organization.name}' (id={org_id}) in contest {contest_id}.")
        return organization.id or org_id, False

