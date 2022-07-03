import nox
from nox.sessions import Session


@nox.session(python=["3.8", "3.9", "3.10"])
def tests(session: Session) -> None:
    session.run("pip", "--version")
    session.run("pdm", "sync")
    session.install("httpx")

    session.run("python", "-m", "unittest")


@nox.session(python="3.10")
def coverage(session: Session) -> None:
    session.run("pdm", "sync")
    session.install("coverage[toml]")
    session.install("codecov")
    session.install("httpx")
    session.run("coverage", "run", "-m", "unittest", "discover")
    session.run("codecov", *session.posargs)
