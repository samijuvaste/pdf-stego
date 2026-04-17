from nox import Session, options, param, parametrize
from nox_uv import session

options.error_on_external_run = True
options.default_venv_backend = "uv"
options.sessions = ["lint", "type_check", "test"]


@session(
    python=["3.10", "3.11", "3.12", "3.13", "3.14", "3.14t"],
    uv_groups=["test"],
)
def test(s: Session) -> None:
    s.run(
        "pytest",
        "--cov=pdf_stego",
        "--cov-report=html",
        "--cov-report=term",
        "tests",
        *s.posargs,
    )


@session(uv_only_groups=["lint"])
@parametrize(
    "command",
    [
        param(
            [
                "ruff",
                "check",
                ".",
                "--select",
                "I",
                "--select",
                "F401",
                "--extend-fixable",
                "F401",
                "--fix",
            ],
            id="sort_imports",
        ),
        param(["ruff", "format", "."], id="format"),
    ],
)
def fmt(s: Session, command: list[str]) -> None:
    s.run(*command)


@session(uv_only_groups=["lint"])
@parametrize(
    "command",
    [
        param(["ruff", "check", "."], id="lint_check"),
        param(["ruff", "format", "--check", "."], id="format_check"),
    ],
)
def lint(s: Session, command: list[str]) -> None:
    s.run(*command)


@session(uv_only_groups=["lint"])
def lint_fix(s: Session) -> None:
    s.run("ruff", "check", ".", "--extend-fixable", "F401", "--fix")


@session(uv_only_groups=["type_check"])
def type_check(s: Session) -> None:
    s.run("mypy", "src", "tests", "noxfile.py")
