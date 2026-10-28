# PyInstaller entry points at the formal package CLI; no examples are bundled.
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

repo_root = Path(SPECPATH).parent
package_root = repo_root / 'src' / 'robots_open_duck'
# The SSH client sends this source to the Pi. Frozen Python modules alone do
# not provide a readable pi_bridge.py file beside ssh_io.py.
datas = [
    (str(package_root / 'pi_bridge.py'), 'robots_open_duck'),
    (str(package_root / 'pi_rl_bridge.py'), 'robots_open_duck'),
]
datas += copy_metadata('open-duck', recursive=True)
try:
    datas += copy_metadata('rustypot')
except PackageNotFoundError:
    pass  # The SSH backend does not require native Rustypot on the PC.
a = Analysis([str(repo_root / 'scripts' / 'pyinstaller_entry.py')], pathex=[str(repo_root / 'src')], binaries=[], datas=datas, hiddenimports=collect_submodules('robots_open_duck'), hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['mujoco'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='robots_open_duck', console=True)
