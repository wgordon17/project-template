"""Smoke tests for template rendering."""

import pytest

from conftest import (
    assert_files_absent,
    assert_files_present,
    check_file_contents,
    parse_json,
    parse_toml,
    parse_yaml,
)


# --- Core rendering (session-scoped, all platforms) ---


def test_renders_without_error(generated_project):
    """Template renders without error for all platforms."""
    assert generated_project.exists()
    assert any(generated_project.iterdir()), "Output directory is empty"


def test_readme_content(generated_project):
    """README.md contains project name and description."""
    readme = generated_project / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "test-project" in content
    assert "A test project" in content


# --- URL derivation (truly tests regex derivation) ---


@pytest.mark.parametrize(
    "repo_url,expected_platform,expected_org,expected_name",
    [
        (
            "https://github.com/myorg/myproject.git",
            "github",
            "myorg",
            "myproject",
        ),
        (
            "git@gitlab.com:mygroup/myrepo.git",
            "gitlab",
            "mygroup",
            "myrepo",
        ),
    ],
)
def test_repo_url_derivation(
    generate, repo_url, expected_platform, expected_org, expected_name
):
    """Copier derives project_name, hosting_platform, hosting_org from repo_url."""
    project = generate(
        _skip_defaults=True,
        repo_url=repo_url,
        project_description="A test project",
    )
    answers = parse_yaml(project / ".copier-answers.yaml")
    assert answers["project_name"] == expected_name
    assert answers["hosting_platform"] == expected_platform
    assert answers["hosting_org"] == expected_org


def test_empty_url_uses_explicit(generate):
    """Empty repo_url falls back to explicitly provided values."""
    project = generate(
        repo_url="",
        project_name="explicit-name",
        hosting_platform="github",
        hosting_org="explicit-org",
    )
    answers = parse_yaml(project / ".copier-answers.yaml")
    assert answers["project_name"] == "explicit-name"
    assert answers["hosting_platform"] == "github"
    assert answers["hosting_org"] == "explicit-org"


# --- Default project structure (session-scoped github) ---


def test_default_project_structure(generated_github_project):
    """Default github project has all expected files."""
    assert_files_present(
        generated_github_project,
        "flake.nix",
        "lib/nix/base.nix",
        "lib/nix/project.nix",
        "lib/just/base.just",
        ".envrc",
        "justfile",
        "prek.toml",
        "cog.toml",
        ".editorconfig",
        ".gitignore",
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        ".copier-answers.yaml",
        ".idea/modules.xml",
        ".idea/test-project.iml",
    )
    assert_files_absent(
        generated_github_project, "copier.yaml", "template", "includes", "hack", "tests", "pytest.ini"
    )


def test_justfile_imports_base(generated_github_project):
    """justfile imports lib/just/base.just."""
    assert "import 'lib/just/base.just'" in (generated_github_project / "justfile").read_text()


def test_envrc_content(generated_github_project):
    """`.envrc` contains `use flake`."""
    assert "use flake" in (generated_github_project / ".envrc").read_text()


def test_copier_answers_valid_yaml(generated_github_project):
    """.copier-answers.yaml is valid YAML with expected keys."""
    answers = parse_yaml(generated_github_project / ".copier-answers.yaml")
    assert "project_name" in answers
    assert "hosting_platform" in answers


# --- Platform-conditional rendering ---


def test_prek_valid_toml(generated_project):
    """prek.toml renders as valid TOML for all platforms."""
    parse_toml(generated_project / "prek.toml")


def test_prek_repos_have_hooks(generated_project):
    """Every [[repos]] entry in prek.toml has at least one hook."""
    data = parse_toml(generated_project / "prek.toml")
    for repo in data.get("repos", []):
        assert repo.get("hooks"), f"Repo {repo.get('repo', 'local')} has no hooks"


def test_cog_valid_toml(generated_project):
    """cog.toml renders as valid TOML for all platforms."""
    parse_toml(generated_project / "cog.toml")


def test_cog_branch(generated_github_project):
    """cog.toml branch_whitelist contains main."""
    data = parse_toml(generated_github_project / "cog.toml")
    assert "main" in data["branch_whitelist"]


def test_prek_github_hooks(generated_github_project):
    """GitHub platform includes actionlint hook."""
    assert "actionlint" in (generated_github_project / "prek.toml").read_text()


@pytest.mark.parametrize("hosting_platform", ["gitlab", "other"])
def test_prek_no_github_hooks(generate, hosting_platform):
    """Non-GitHub platforms do not include actionlint hook."""
    project = generate(hosting_platform=hosting_platform)
    assert "actionlint" not in (project / "prek.toml").read_text()


def test_editorconfig_content(generated_github_project):
    """.editorconfig has expected settings."""
    content = (generated_github_project / ".editorconfig").read_text()
    assert "root = true" in content
    assert "end_of_line = lf" in content
    assert "indent_style = tab" in content


def test_gitignore_content(generated_github_project):
    """.gitignore has expected entries."""
    content = (generated_github_project / ".gitignore").read_text()
    assert ".direnv/" in content
    assert "result/" in content


def test_readme_sections(generated_project):
    """README has Getting Started and Recipes sections."""
    content = (generated_project / "README.md").read_text()
    assert "Getting Started" in content
    assert "Recipes" in content


def test_license_content(generated_github_project):
    """LICENSE has MIT license with hosting_org."""
    content = (generated_github_project / "LICENSE").read_text()
    assert "test-org" in content
    assert "MIT License" in content


def test_contributing_content(generated_github_project):
    """CONTRIBUTING.md references Conventional Commits."""
    assert "Conventional Commits" in (generated_github_project / "CONTRIBUTING.md").read_text()


def test_contributing_update_recipe(generated_github_project):
    """CONTRIBUTING.md documents just update for template updates."""
    assert "just update" in (generated_github_project / "CONTRIBUTING.md").read_text()


# --- GitHub integration ---


def test_nix_setup_action(generated_github_project):
    """GitHub projects have SHA-pinned nix-setup composite action."""
    action = generated_github_project / ".github" / "actions" / "nix-setup" / "action.yaml"
    assert action.exists()
    content = action.read_text()
    assert "composite" in content
    assert "nix-installer-action@" in content


@pytest.mark.parametrize("hosting_platform", ["gitlab", "other"])
def test_github_files_absent(generate, hosting_platform):
    """Non-GitHub platforms have no .github/ files."""
    project = generate(hosting_platform=hosting_platform)
    github_dir = project / ".github"
    if github_dir.exists():
        files = list(github_dir.rglob("*"))
        assert not files, f"Unexpected .github/ files for {hosting_platform}: {files}"


def test_pr_checks_valid_yaml(generated_github_project):
    """pr-checks.yaml is valid YAML with expected structure."""
    data = parse_yaml(generated_github_project / ".github" / "workflows" / "pr-checks.yaml")
    assert "jobs" in data
    assert "checks" in data["jobs"]


def test_pr_checks_has_steps(generated_github_project):
    """pr-checks has lint, test, and integration test steps."""
    content = (generated_github_project / ".github" / "workflows" / "pr-checks.yaml").read_text()
    assert "just lint" in content
    assert "just test" in content
    assert "just test-integration" in content


def test_pr_checks_pinned_actions(generated_github_project):
    """All uses: refs in pr-checks are SHA-pinned."""
    content = (generated_github_project / ".github" / "workflows" / "pr-checks.yaml").read_text()
    for line in content.splitlines():
        if "uses:" in line and "@" in line:
            ref = line.split("@")[1].split()[0]
            assert len(ref) >= 40 or ref.startswith("./"), f"Unpinned action: {line.strip()}"


def test_renovate_config_valid_json(generated_github_project):
    """renovate.json is valid JSON with expected keys."""
    data = parse_json(generated_github_project / ".github" / "renovate.json")
    assert "extends" in data
    assert "customManagers" in data


def test_renovate_no_template_config(generated_github_project):
    """Default projects don't have template-specific Renovate managers."""
    content = (generated_github_project / ".github" / "renovate.json").read_text()
    assert "postUpgradeTasks" not in content
    assert "template/" not in content


def test_security_md(generated_github_project):
    """GitHub projects have SECURITY.md with project name."""
    security = generated_github_project / ".github" / "SECURITY.md"
    assert security.exists()
    check_file_contents(security, expected=("test-project",))


@pytest.mark.parametrize("hosting_platform", ["gitlab", "other"])
def test_security_md_absent(generate, hosting_platform):
    """Non-GitHub platforms don't have SECURITY.md."""
    project = generate(hosting_platform=hosting_platform)
    assert_files_absent(project, ".github/SECURITY.md")


# --- _is_template conditional ---


def test_renovate_has_template_config(generated_template_project):
    """Template repo (_is_template=True) has template-specific managers."""
    data = parse_json(generated_template_project / ".github" / "renovate.json")
    managers = data.get("customManagers", [])
    template_managers = [m for m in managers if any("template/" in f for f in m.get("managerFilePatterns", []))]
    assert template_managers, "No template-specific customManagers found"


def test_no_consistency_job_default(generated_github_project):
    """Default projects have no consistency job in pr-checks."""
    assert "consistency" not in (generated_github_project / ".github" / "workflows" / "pr-checks.yaml").read_text()


def test_has_consistency_job_template(generated_template_project):
    """Template repo (_is_template=True) has consistency job."""
    assert "consistency" in (generated_template_project / ".github" / "workflows" / "pr-checks.yaml").read_text()


def test_idea_xml_valid(generated_github_project):
    """JetBrains modules.xml is valid XML."""
    import xml.etree.ElementTree as ET
    ET.parse(generated_github_project / ".idea" / "modules.xml")


def test_base_just_has_update(generated_github_project):
    """base.just includes the update recipe."""
    content = (generated_github_project / "lib" / "just" / "base.just").read_text()
    assert "update:" in content
    assert "--answers-file" in content


def test_readme_no_template_quickstart(generated_github_project):
    """Default projects don't show template quickstart in README."""
    content = (generated_github_project / "README.md").read_text()
    assert "From template" not in content
    assert "gordon-code/project-template" not in content


def test_readme_template_quickstart(generated_template_project):
    """Template repo README shows quickstart for creating new projects."""
    content = (generated_template_project / "README.md").read_text()
    assert "From template" in content
    assert "copier copy" in content


def test_base_nix_uses_pkgs_prek(generated_github_project):
    """base.nix uses pkgs.prek directly (no binary-fetch overlay)."""
    content = (generated_github_project / "lib" / "nix" / "base.nix").read_text()
    assert "pkgs.prek" in content
    assert "fetchurl" not in content
    assert "TODO" not in content


def test_nix_setup_no_telemetry(generated_github_project):
    """nix-setup action disables Determinate Systems telemetry."""
    content = (generated_github_project / ".github" / "actions" / "nix-setup" / "action.yaml").read_text()
    assert 'diagnostic-endpoint: ""' in content
