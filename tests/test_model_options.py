from types import SimpleNamespace

from application.service import ModelOptions


def test_model_options_use_config_default_for_phi4(monkeypatch) -> None:
    monkeypatch.setattr(
        ModelOptions,
        "get_runtime_config",
        lambda: SimpleNamespace(ufc_model_name="phi4:latest"),
    )

    options = ModelOptions.build_llm_model_options()

    assert options[0].label == "phi4"
    assert options[0].model_name == "phi4:latest"


def test_model_options_include_exact_runtime_choices(monkeypatch) -> None:
    monkeypatch.setattr(
        ModelOptions,
        "get_runtime_config",
        lambda: SimpleNamespace(ufc_model_name="phi4:latest"),
    )

    assert ModelOptions.get_llm_model_names() == (
        "phi4:latest",
        "llama3.1:8b",
        "qwen3:14b",
        "deepseek-r1:14b",
    )


def test_model_options_come_from_runtime_config(monkeypatch) -> None:
    monkeypatch.setattr(
        ModelOptions,
        "get_runtime_config",
        lambda: SimpleNamespace(
            ufc_model_name="phi4:latest",
            llm_model_options=(
                SimpleNamespace(label="default", model_name="phi4:latest"),
                SimpleNamespace(label="custom", model_name="custom-model:7b"),
            ),
        ),
    )

    assert ModelOptions.get_llm_model_labels() == {
        "phi4:latest": "default",
        "custom-model:7b": "custom",
    }


def test_invalid_model_falls_back_to_config_default(monkeypatch) -> None:
    monkeypatch.setattr(
        ModelOptions,
        "get_runtime_config",
        lambda: SimpleNamespace(ufc_model_name="phi4:latest"),
    )

    assert ModelOptions.coerce_llm_model_name("qwen2.5:14b") == "phi4:latest"


def test_valid_model_is_preserved(monkeypatch) -> None:
    monkeypatch.setattr(
        ModelOptions,
        "get_runtime_config",
        lambda: SimpleNamespace(ufc_model_name="phi4:latest"),
    )

    assert ModelOptions.coerce_llm_model_name("qwen3:14b") == "qwen3:14b"
