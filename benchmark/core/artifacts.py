"""Atomic checkpoints and source loading; no study-specific execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from benchmark.core.bootstrap import PROJECT_ROOT
from benchmark.evaluation.literal import canonical

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source_corpus(anchors):
    return {name: canonical((PROJECT_ROOT / "data/collections/uploaded_files" / name).read_text())
            for name in {a["document"] for a in anchors.values()}}


class Recorder:
    """Resume only an identical experiment; never overwrite frozen artifacts."""

    def __init__(self, output, mode, signature):
        self.path = output / f"{mode}.json"
        if self.path.exists():
            self.data = read_json(self.path)
            if self.data["signature"] != signature:
                raise ValueError("Experiment signature changed; use a new output directory")
        else:
            self.data = {"mode": mode, "started_at": datetime.now(timezone.utc).isoformat(),
                         "signature": signature, "results": []}
        self.done = {x["key"] for x in self.data["results"]}

    def add(self, key, **value):
        if key in self.done:
            return
        self.data["results"].append({"key": key, **value})
        self.done.add(key)
        save_json(self.path, self.data)
        print(f"{self.data['mode']} {key}: {value.get('status', 'ok')}", flush=True)

    def finish(self, **summary):
        self.data.update(summary=summary, finished_at=datetime.now(timezone.utc).isoformat())
        save_json(self.path, self.data)

