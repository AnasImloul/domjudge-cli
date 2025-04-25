import base64
import requests
from dom.types.api import models


class DomjudgeAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

        # Encode username:password into Base64 for Basic Auth
        credentials = f"{self.username}:{self.password}"
        credentials_bytes = credentials.encode('utf-8')
        base64_credentials = base64.b64encode(credentials_bytes).decode('utf-8')

        self.session.headers.update({
            "Authorization": f"Basic {base64_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_user(self, user_id: int) -> models.User:
        """
        GET /api/v4/users/{user_id}/
        """
        response = self.session.get(self._url(f"/api/v4/users/{user_id}/"))
        response.raise_for_status()
        return models.User(**response.json())

    def list_contests(self) -> list:
        """
        GET /api/v4/contests
        """
        response = self.session.get(self._url("/api/v4/contests"))
        response.raise_for_status()
        return response.json()

    def create_contest(self, contest_data: dict) -> dict:
        """
        POST /api/v4/contests
        """
        response = self.session.post(self._url("/api/v4/contests"), json=contest_data)
        response.raise_for_status()
        return response.json()

    def update_contest(self, contest_id: int, contest_data: dict) -> dict:
        """
        PUT /api/v4/contests/{contest_id}/
        """
        response = self.session.put(self._url(f"/api/v4/contests/{contest_id}/"), json=contest_data)
        response.raise_for_status()
        return response.json()

    def delete_contest(self, contest_id: int) -> None:
        """
        DELETE /api/v4/contests/{contest_id}/
        """
        response = self.session.delete(self._url(f"/api/v4/contests/{contest_id}/"))
        response.raise_for_status()

    def sync_contests(contests: list) -> None:
        for contest in contests:
            print(f"⚡ Syncing contest: {contest.get('name')}")
        # Real API communication would go here later


if __name__ == '__main__':
    client = DomjudgeAPI(
        base_url="http://localhost",
        username="admin",
        password="--OEKyfW4pQb4ai9"
    )