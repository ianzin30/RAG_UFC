"""Legacy module names for code that moved into ``rag_ufc_core``.

Benchmarks, frozen experiment scripts and tests import the engine as
``service.rag.v2.*`` or ``application.service.rag.v2.*``. Those names now resolve to
the *same module objects* as ``rag_ufc_core.*`` (one copy per process, so classes,
monkeypatches and module state agree). The files at the old paths are symlinks to
the package sources, so tools that hash or archive files by path keep reading the
exact bytes that run.

``service.RuntimeConfig`` is also unified with ``application.service.RuntimeConfig``
when both roots are importable: it holds the checkout state the core is bound to
(configuration reader, secret source, caches), which must not exist twice.
"""

import importlib
import importlib.abc
import importlib.util
import sys

LEGACY_ROOTS = ("service", "application.service")
MOVED = {
    "rag.v2": "rag_ufc_core.rag.v2",
    "rag.CrewAiTelemetry": "rag_ufc_core.rag.CrewAiTelemetry",
    "UfcOllama": "rag_ufc_core.UfcOllama",
    "StructuredExtraction": "rag_ufc_core.StructuredExtraction",
    "SpreadsheetMarkdown": "rag_ufc_core.SpreadsheetMarkdown",
    "spreadsheet": "rag_ufc_core.spreadsheet",
}


SHARED_CHECKOUT_MODULES = {"service.RuntimeConfig": "application.service.RuntimeConfig"}


def core_name(fullname):
    if fullname in SHARED_CHECKOUT_MODULES and importlib.util.find_spec("application") is not None:
        return SHARED_CHECKOUT_MODULES[fullname]
    for root in LEGACY_ROOTS:
        if not fullname.startswith(root + "."):
            continue
        rest = fullname[len(root) + 1:]
        for legacy, target in MOVED.items():
            if rest == legacy or rest.startswith(legacy + "."):
                return target + rest[len(legacy):]
    return None


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target):
        self.target = target

    def create_module(self, spec):
        self.module = importlib.import_module(self.target)
        self.original_spec = self.module.__spec__
        return self.module

    def exec_module(self, module):
        # The import system stamps the alias spec on the module; keep the real one so
        # relative imports and reloads keep using rag_ufc_core names.
        module.__spec__ = self.original_spec


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        name = core_name(fullname)
        if name is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(name))


def install():
    if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())
