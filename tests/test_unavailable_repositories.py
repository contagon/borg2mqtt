import subprocess
from collections.abc import Callable

import pytest

from borg2mqtt import actions
from borg2mqtt.repo import MQTTSettings, Repository


@pytest.mark.parametrize(
    ("action", "method_name"),
    [(actions.setup, "setup"), (actions.update, "update")],
)
def test_unavailable_repository_does_not_stop_later_repositories(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    action: Callable[[list[Repository], MQTTSettings], None],
    method_name: str,
):
    repos = [
        Repository("first"),
        Repository("offline"),
        Repository("last"),
    ]
    calls: list[str] = []

    def operation(repo: Repository, mqtt: MQTTSettings):
        calls.append(repo.repo)
        if repo.repo == "offline":
            raise subprocess.CalledProcessError(2, ["borg", method_name])

    monkeypatch.setattr(Repository, method_name, operation)

    with pytest.raises(SystemExit) as error:
        action(repos, MQTTSettings())

    assert error.value.code == 1
    assert calls == ["first", "offline", "last"]
    assert "[borg2mqtt][offline] Borg exited with status 2" in capsys.readouterr().err


def test_successful_repositories_exit_normally(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def update(repo: Repository, mqtt: MQTTSettings):
        calls.append(repo.repo)

    monkeypatch.setattr(Repository, "update", update)

    actions.update([Repository("first"), Repository("last")], MQTTSettings())

    assert calls == ["first", "last"]


def test_unrelated_errors_are_not_hidden(monkeypatch: pytest.MonkeyPatch):
    def update(repo: Repository, mqtt: MQTTSettings):
        raise RuntimeError("bad response")

    monkeypatch.setattr(Repository, "update", update)

    with pytest.raises(RuntimeError, match="bad response"):
        actions.update([Repository("repo")], MQTTSettings())


def test_borg_nonzero_exit_is_reported(monkeypatch: pytest.MonkeyPatch):
    called_with_check = False

    def run(
        *_args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal called_with_check
        called_with_check = kwargs.get("check") is True
        raise subprocess.CalledProcessError(2, ["borg", "info"])

    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(subprocess.CalledProcessError):
        Repository("offline").update(MQTTSettings())

    assert called_with_check
