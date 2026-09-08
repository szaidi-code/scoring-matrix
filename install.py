#!/usr/bin/env python3
"""Install/remove the Scoring Matrix application-menu entry for the current user."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

FILES = ('scoring_matrix.py', 'MATRIX.md', 'LICENSE')


def desktop_quote(value):
    # Avoid undefined percent field-code expansion inside quoted arguments.
    if any(c in str(value) for c in ('%', '\n', '\r')):
        raise ValueError('Installation paths containing %, newline or carriage return are unsupported.')
    result = str(value).replace('\\', '\\\\\\\\')
    for c in ('"', '`', '$'):
        result = result.replace(c, '\\\\' + c)
    return '"' + result + '"'


def install(data_home, source, uninstall=False):
    data_home = Path(data_home).expanduser().absolute()
    app = data_home / 'scoring-matrix'
    desktop = data_home / 'applications/scoring-matrix.desktop'
    if app.is_symlink() or desktop.is_symlink():
        raise ValueError('Refusing to overwrite a symlink at an installation target.')
    marker = app / 'installation.json'
    if app.exists() and (not marker.is_file() or json.loads(marker.read_text()).get('app') != 'scoring-matrix'):
        raise ValueError('Existing installation directory is not owned by this installer.')
    if desktop.exists() and 'X-ScoringMatrix-Managed=true' not in desktop.read_text():
        raise ValueError('Existing desktop entry is not owned by this installer.')
    for name in (*FILES, 'installation.json'):
        if (app/name).is_symlink():
            raise ValueError('Refusing to overwrite an installed symlink.')
    if uninstall:
        if marker.exists():
            for name in (*FILES, 'installation.json'):
                (app/name).unlink(missing_ok=True)
            # Preserve any user-added files and reports.
            if not any(app.iterdir()):
                app.rmdir()
        desktop.unlink(missing_ok=True)
        print('Removed application launcher. Saved reports and native shell plugin are preserved.')
        return desktop
    executable = str(Path(sys.executable).resolve())
    exec_line = f'{desktop_quote(executable)} {desktop_quote(app / "scoring_matrix.py")} --menu'
    app.mkdir(parents=True, exist_ok=True)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(Path(source)/name, app/name)
    marker.write_text(json.dumps({'app': 'scoring-matrix', 'version': json.loads((Path(source)/'manifest.json').read_text())['version']}))
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Scoring Matrix\n'
                       'Comment=Score this computer for Omarchy and compare your devices\n'
                       f'Exec={exec_line}\nTerminal=true\nIcon=utilities-system-monitor\n'
                       'Categories=System;Utility;\nKeywords=Omarchy;Hardware;Score;Resources;\n'
                       'X-ScoringMatrix-Managed=true\n', encoding='utf-8')
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(desktop.parent)], check=False)
    print('Installed: ' + str(desktop))
    print('Open your application launcher and search for Scoring Matrix.')
    return desktop


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--uninstall', action='store_true')
    a = p.parse_args()
    if sys.platform != 'linux':
        p.error('Run this installer on Omarchy/Linux. Use windows/OmarchyScore.ps1 on Windows.')
    try:
        install(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')), Path(__file__).parent, a.uninstall)
    except (OSError, ValueError) as e:
        raise SystemExit(str(e))
