"""Official application launcher: project TOML -> native Streamlit flags."""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_command(extra=()):
    config = tomllib.loads((ROOT / 'config/config.toml').read_text())
    native = config.get('streamlit', {})
    allowed = {'server': {'address', 'port', 'headless'},
               'theme': {'base', 'primaryColor', 'backgroundColor', 'secondaryBackgroundColor', 'textColor', 'font'}}
    result = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'application/app.py'), '--browser.gatherUsageStats=false']
    for section, names in allowed.items():
        for key, value in native.get(section, {}).items():
            if key not in names:
                raise ValueError(f'Opção nativa não permitida: {section}.{key}')
            result.append(f'--{section}.{key}={str(value).lower() if isinstance(value, bool) else value}')
    return result + list(extra)


if __name__ == '__main__':
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.chdir(ROOT)
    os.execv(sys.executable, build_command(sys.argv[1:]))
