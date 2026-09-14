"""
F01 SENTINEL — Module sentinel_gh
GitHub API : wrappers actifs, issues, étoiles pour une API donnée
"""
import os
import httpx


GH_API = "https://api.github.com"
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GH_TOKEN:
        h["Authorization"] = f"token {GH_TOKEN}"
    return h


def search_wrappers(api_host: str, max_results: int = 30) -> dict:
    """Cherche repos qui importent cette API RapidAPI."""
    query = f'"{api_host}" language:python'
    try:
        resp = httpx.get(
            f"{GH_API}/search/code",
            params={"q": query, "per_page": max_results},
            headers=_headers(),
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        repos = {}
        for item in items:
            r = item.get("repository", {})
            full_name = r.get("full_name", "")
            if full_name not in repos:
                repos[full_name] = {
                    "full_name": full_name,
                    "description": r.get("description", ""),
                    "stars": r.get("stargazers_count", 0),
                    "url": r.get("html_url", "")
                }
        return {
            "api_host": api_host,
            "total_wrappers": data.get("total_count", 0),
            "repos": list(repos.values()),
            "status": "ok"
        }
    except Exception as e:
        return {"api_host": api_host, "total_wrappers": 0, "repos": [], "status": "error", "error": str(e)}


def get_repo_activity(full_name: str) -> dict:
    """Récupère métadonnées et issues ouvertes d'un repo."""
    try:
        repo_resp = httpx.get(f"{GH_API}/repos/{full_name}", headers=_headers(), timeout=15)
        repo_resp.raise_for_status()
        repo = repo_resp.json()

        issues_resp = httpx.get(
            f"{GH_API}/repos/{full_name}/issues",
            params={"state": "open", "per_page": 5},
            headers=_headers(),
            timeout=15
        )
        issues = issues_resp.json() if issues_resp.status_code == 200 else []

        return {
            "full_name": full_name,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "last_push": repo.get("pushed_at", ""),
            "recent_issues": [i.get("title", "") for i in issues[:5]],
            "status": "ok"
        }
    except Exception as e:
        return {"full_name": full_name, "status": "error", "error": str(e)}
