import pytest

from sbretire import __version__
from sbretire.__main__ import build_parser


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.config == "config/model.yaml"
    assert args.output_dir == "output"
