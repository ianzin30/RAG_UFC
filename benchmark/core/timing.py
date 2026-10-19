"""Checkpointed physical wall time; cached historical costs never enter it."""
from contextlib import contextmanager
from datetime import datetime, timezone
import time

from benchmark.core.artifacts import read_json, save_json


class RunClock:
    def __init__(self, path, monotonic=time.perf_counter, now=None):
        self.path, self.monotonic = path, monotonic
        self.now = now or (lambda: datetime.now(timezone.utc).isoformat())
        self.data = read_json(path) if path.exists() else {'started_at': self.now(), 'sessions': []}
        for session in self.data['sessions']:
            if session['status'] == 'running':
                session.update(status='interrupted', unobserved_tail='unknown; only checkpointed duration counted')
        self.session = {'started_at': self.now(), 'status': 'running', 'active_seconds': 0., 'phases': {}}
        self.data['sessions'].append(self.session)
        self.started = self.monotonic()
        self.phase = 'preparation'
        self.phase_started = self.started
        self.flush()

    def flush(self):
        now = self.monotonic()
        self.session['active_seconds'] = now - self.started
        self.session['phases'][self.phase] = self.session['phases'].get(self.phase, 0.) + now - self.phase_started
        self.phase_started = now
        self.session['updated_at'] = self.now()
        self.data['updated_at'] = self.session['updated_at']
        self.data['active_wall_seconds'] = sum(s['active_seconds'] for s in self.data['sessions'])
        self.data['elapsed_since_first_start_seconds'] = (
            datetime.fromisoformat(self.data['updated_at']) - datetime.fromisoformat(self.data['started_at'])).total_seconds()
        save_json(self.path, self.data)

    def set_phase(self, phase):
        self.flush()
        self.phase = phase

    @contextmanager
    def measure(self, kind):
        start = self.monotonic()
        try:
            yield
        finally:
            self.session[kind + '_seconds'] = self.session.get(kind + '_seconds', 0.) + self.monotonic() - start
            self.flush()

    def finish(self, status):
        self.flush()
        self.session.update(status=status, finished_at=self.now())
        self.data.update(status=status, finished_at=self.session['finished_at'])
        save_json(self.path, self.data)
