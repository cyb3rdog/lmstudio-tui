from __future__ import annotations

import pytest

from lmstudio_tui.api.models import ModelInfo, ModelState, ModelsResponse


class TestModelsResponseFromRaw:
    def test_lmstudio_format_parses_models_key(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        models = resp.model_list
        assert len(models) == 3

    def test_lmstudio_format_maps_key_to_id(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        ids = [m.id for m in resp.model_list]
        assert "llama-3-8b-instruct-q4_K_M" in ids
        assert "mistral-7b-instruct-q8_0" in ids

    def test_lmstudio_format_extracts_instance_id(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        loaded = resp.model_list[0]
        assert loaded.instance_id == "llama-3-8b-instruct-q4_K_M:0"

    def test_lmstudio_format_unloaded_model_has_no_instance_id(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        unloaded = resp.model_list[1]
        assert unloaded.instance_id is None

    def test_lmstudio_format_extracts_quantization_name_from_dict(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        model = resp.model_list[0]
        assert model.quantization == "Q4_K_M"

    def test_lmstudio_format_null_quantization_is_none(self, lmstudio_models_response):
        resp = ModelsResponse.from_raw(lmstudio_models_response)
        model = resp.model_list[2]  # phi-3-mini has null quantization
        assert model.quantization is None

    def test_openai_format_parses_data_key(self, openai_models_response):
        resp = ModelsResponse.from_raw(openai_models_response)
        models = resp.model_list
        assert len(models) == 2
        assert models[0].id == "gpt-4"

    def test_empty_response_returns_empty_list(self):
        resp = ModelsResponse.from_raw({})
        assert resp.model_list == []

    def test_extra_unknown_fields_are_ignored(self):
        raw = {
            "models": [
                {
                    "key": "test-model",
                    "unknown_field_xyz": "should be ignored",
                    "loaded_instances": [],
                }
            ]
        }
        resp = ModelsResponse.from_raw(raw)
        assert len(resp.model_list) == 1
        assert resp.model_list[0].id == "test-model"


class TestModelInfoIsLoaded:
    def test_loaded_state_returns_true(self):
        m = ModelInfo(id="test", state=ModelState.LOADED)
        assert m.is_loaded is True

    def test_not_loaded_state_returns_false(self):
        m = ModelInfo(id="test", state=ModelState.NOT_LOADED)
        assert m.is_loaded is False

    def test_instance_id_without_state_returns_true(self):
        m = ModelInfo(id="test", instance_id="test:0")
        assert m.is_loaded is True

    def test_no_state_no_instance_id_returns_false(self):
        m = ModelInfo(id="test")
        assert m.is_loaded is False

    def test_loading_state_returns_false(self):
        m = ModelInfo(id="test", state=ModelState.LOADING)
        assert m.is_loaded is False


class TestModelInfoCoercions:
    def test_unknown_state_string_becomes_none(self):
        m = ModelInfo.model_validate({"id": "x", "state": "UNKNOWN_FUTURE_VALUE"})
        assert m.state is None

    def test_state_is_case_insensitive(self):
        m = ModelInfo.model_validate({"id": "x", "state": "LOADED"})
        assert m.state == ModelState.LOADED

    def test_none_state_stays_none(self):
        m = ModelInfo.model_validate({"id": "x", "state": None})
        assert m.state is None

    def test_quantization_dict_extracts_name(self):
        m = ModelInfo.model_validate({"id": "x", "quantization": {"name": "Q4_K_M", "bits": 4}})
        assert m.quantization == "Q4_K_M"

    def test_quantization_string_passes_through(self):
        m = ModelInfo.model_validate({"id": "x", "quantization": "Q4_K_M"})
        assert m.quantization == "Q4_K_M"

    def test_quantization_none_stays_none(self):
        m = ModelInfo.model_validate({"id": "x", "quantization": None})
        assert m.quantization is None

    def test_model_validate_ignores_extra_fields(self):
        m = ModelInfo.model_validate({"id": "x", "totally_unknown": True})
        assert m.id == "x"
