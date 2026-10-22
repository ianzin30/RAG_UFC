"""Research-checkout services around the shared ``rag_ufc_core`` package.

Importing this package binds the core to this checkout: legacy module names,
``config/config.toml`` as the default settings document and ``.env`` as the
secret source. Installed applications make these choices themselves.
"""

from . import _core_aliases

_core_aliases.install()


def _bind_checkout():
    from rag_ufc_core import secret_source
    from rag_ufc_core.rag.v2 import Config

    from . import RuntimeConfig

    Config.use_default_document(RuntimeConfig.checkout_settings_document)
    secret_source.use_secret_source(RuntimeConfig.read_secret)


_bind_checkout()
