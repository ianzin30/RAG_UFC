"""Warning and logging suppression for benchmark execution.

Suppresses noisy, non-critical warnings from third-party libraries while
preserving important error messages and benchmark-related output.
"""

import logging
import warnings


def suppress_noisy_warnings() -> None:
    """Suppress non-critical third-party warnings that clutter benchmark output.

    Suppressed warnings:
    - torch_dtype deprecation (expected, will upgrade when available)
    - bitsandbytes FutureWarnings (safe, non-critical)
    - triton warnings (informational only)
    - transformers/huggingface warnings (non-critical)

    Preserves:
    - Real errors and exceptions
    - Critical deprecations
    - Benchmark-related output
    """

    # Suppress specific warning categories by module
    warnings.filterwarnings("ignore", category=FutureWarning, module="bitsandbytes.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*torch.*dtype.*")
    warnings.filterwarnings("ignore", message=".*triton not found.*")
    warnings.filterwarnings("ignore", category=UserWarning, module=".*transformers.*")
    warnings.filterwarnings("ignore", message=".*_check_is_size will be removed.*")

    # Suppress INFO and WARNING level logs from specific modules
    logging.getLogger("torch").setLevel(logging.ERROR)
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("bitsandbytes").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    # Suppress torch/CUDA initialization warnings
    logging.getLogger("torch.cuda").setLevel(logging.ERROR)
    logging.getLogger("torch.utils.flop_counter").setLevel(logging.ERROR)
