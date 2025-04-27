import base64
import requests
import os
from requests.auth import HTTPBasicAuth
import json
import tempfile
from pathlib import Path

from dom.core.services.problem.converter.models import ProblemPackage
from dom.types.api import models
from io import BytesIO

class DomjudgeAPI:
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
            return response.json(), True

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

    def add_team_to_contest(self, contest_id: str, team_data: models.AddTeam) -> str:
        for team in self.list_contest_teams(contest_id):
            if team["name"] == team_data.name:
                print(f"[INFO] Team with name '{team_data.name}' already exists for this contest_id {contest_id}.")
                return team["id"]

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
        return team_id

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
