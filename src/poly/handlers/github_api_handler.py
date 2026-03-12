# Copyright PolyAI Limited
"""GitHub API helper for Agent Studio CLI utilities (e.g. gists)."""

import os
from typing import Any

import requests

GIST_URL = "https://api.github.com/gists"
GITHUB_API_VERSION = "2022-11-28"


class GitHubAPIHandler:
    """Lightweight helper around GitHub REST API used by the CLI."""

    @staticmethod
    def _get_token() -> str:
        """Retrieve the GitHub access token from environment variables.

        Returns:
            The GitHub access token.

        Raises:
            EnvironmentError: If the GITHUB_ACCESS_TOKEN environment variable is not set.
        """
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            raise OSError(
                "GITHUB_ACCESS_TOKEN environment variable not set. "
                "Please set it to your GitHub personal access token with gist scope."
            )
        return token

    @classmethod
    def _headers(cls) -> dict[str, str]:
        """Construct headers for GitHub API requests.

        Returns:
            Dictionary containing Authorization, Accept, and API version headers.
        """
        token = cls._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    @classmethod
    def _request(cls, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Wrapper for requests that injects GitHub headers and handles errors.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: URL to request
            on_404: Optional custom error message to display for 404 responses
            **kwargs: Additional arguments to pass to requests.request

        Returns:
            Response object from the request

        Raises:
            HTTPError: If the request returns an error status code
        """
        headers = kwargs.pop("headers", {})
        merged_headers = {**cls._headers(), **headers}
        resp = requests.request(method, url, headers=merged_headers, **kwargs)
        if resp.status_code == 404:
            raise requests.HTTPError(
                "Failed to make the gist. Your token must be missing gist permissions. Update and try again!"
            )
        resp.raise_for_status()
        return resp

    @classmethod
    def create_gist(
        cls, files: dict[str, dict[str, str]], description: str, public: bool = False
    ) -> str:
        """Create a gist and return its HTML URL."""
        payload = {"description": description, "public": public, "files": files}
        resp = cls._request("POST", GIST_URL, json=payload)
        return resp.json()["html_url"]

    @classmethod
    def list_gists(cls) -> Any:
        """Get the gists made for the reviews of the project."""
        resp = cls._request("GET", GIST_URL)
        return resp.json()

    @classmethod
    def delete_diff_gists(cls) -> list[str]:
        """Delete all review gists (comprised only of .diff files) and return IDs."""
        deleted_ids: list[str] = []
        gists = cls.list_gists()
        for gist in gists:
            # Delete gists comprised only of *.diff files
            if all(file.endswith(".diff") for file in gist["files"]):
                cls._request("DELETE", f"{GIST_URL}/{gist['id']}")
                deleted_ids.append(gist["id"])
        return deleted_ids
