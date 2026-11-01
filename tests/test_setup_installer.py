import importlib.util
from pathlib import Path

SETUP_PATH = Path(__file__).resolve().parents[1] / "setup.py"
SPEC = importlib.util.spec_from_file_location("skyfall_setup", SETUP_PATH)
assert SPEC and SPEC.loader
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


def test_installer_defaults_to_current_user():
    args = setup.build_parser().parse_args([])

    assert setup.is_user_install(args)


def test_system_install_requires_explicit_flag():
    args = setup.build_parser().parse_args(["--system"])

    assert not setup.is_user_install(args)


def test_windows_user_paths_use_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setattr(setup.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))

    app_dir, launcher, desktop_file, share_dir = setup.user_install_paths(tmp_path)

    assert app_dir == tmp_path / "Local" / "Programs" / "SkyFall"
    assert launcher == app_dir / "skyfall.cmd"
    assert desktop_file is None
    assert share_dir is None
    assert setup.venv_python_path(app_dir / "venv") == (
        app_dir / "venv" / "Scripts" / "python.exe"
    )
    setup.write_launcher(launcher, app_dir, True)
    assert '"%~dp0venv\\Scripts\\python.exe"' in launcher.read_text()


def test_macos_user_paths_create_application_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(setup.sys, "platform", "darwin")

    app_dir, launcher, desktop_file, share_dir = setup.user_install_paths(tmp_path)

    assert app_dir == tmp_path / "Library" / "Application Support" / "skyfall"
    assert launcher == (
        tmp_path / "Applications" / "SkyFall.app" / "Contents" / "MacOS" / "skyfall"
    )
    assert desktop_file is None
    assert share_dir is None
