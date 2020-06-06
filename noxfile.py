import nox


@nox.session(python=["3.6", "3.7", "3.8"])
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("pytest", "--cov")
