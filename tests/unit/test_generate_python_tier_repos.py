"""Tests for the Python-tier repo enumerator."""

import json

from scripts.generate_python_tier_repos import python_repos_for_org


def test_python_repos_excludes_exempt(tmp_path):
    catalog = tmp_path / "github-repos.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "BW",
                        "name": "py-app",
                        "repositoryType": "python-app",
                        "branchProtectionExempt": False,
                    },
                    {
                        "org": "BW",
                        "name": "config-only",
                        "repositoryType": "config",
                        "branchProtectionExempt": False,
                    },
                    {
                        "org": "BW",
                        "name": "py-exempt",
                        "repositoryType": "python-app",
                        "branchProtectionExempt": True,
                    },
                    {
                        "org": "WB",
                        "name": "other-py",
                        "repositoryType": "python-script",
                        "branchProtectionExempt": False,
                    },
                ]
            }
        )
    )
    assert python_repos_for_org("BW", catalog) == ["py-app"]
    assert python_repos_for_org("WB", catalog) == ["other-py"]


def test_python_repos_returns_sorted(tmp_path):
    catalog = tmp_path / "github-repos.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "BW",
                        "name": "zeta",
                        "repositoryType": "python-app",
                        "branchProtectionExempt": False,
                    },
                    {
                        "org": "BW",
                        "name": "alpha",
                        "repositoryType": "python-package",
                        "branchProtectionExempt": False,
                    },
                    {
                        "org": "BW",
                        "name": "beta",
                        "repositoryType": "python-script",
                        "branchProtectionExempt": False,
                    },
                ]
            }
        )
    )
    assert python_repos_for_org("BW", catalog) == ["alpha", "beta", "zeta"]


def test_python_repos_empty_when_no_match(tmp_path):
    catalog = tmp_path / "github-repos.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "BW",
                        "name": "config-only",
                        "repositoryType": "config",
                        "branchProtectionExempt": False,
                    },
                ]
            }
        )
    )
    assert python_repos_for_org("BW", catalog) == []
