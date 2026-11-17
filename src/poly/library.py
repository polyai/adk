"""Library module for PolyAI models."""

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from poly.constants import POLY_HOME_DIR

LIBRARY_DIR = os.path.join(POLY_HOME_DIR, "library")


@dataclass
class ASRModel:
    """Library model for ASR models."""

    model_id: str
    name: str
    provider: str
    model: str

    @classmethod
    def from_api_response(cls, api_response: dict) -> "ASRModel":
        return cls(
            model_id=api_response.get("id"),
            name=api_response.get("name"),
            provider=api_response.get("provider"),
            model=api_response.get("model"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.model_id,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
        }


@dataclass
class LLMModel:
    """Library model for LLMs."""

    model_id: str
    name: str
    provider_model_id: str
    poly_ai_model: str
    speech_native: bool
    supports_webchat: bool
    supports_temperature: bool

    @classmethod
    def from_api_response(cls, api_response: dict) -> "LLMModel":
        return cls(
            model_id=api_response.get("id"),
            name=api_response.get("name"),
            provider_model_id=api_response.get("providerModelId"),
            poly_ai_model=api_response.get("polyaiModel"),
            speech_native=api_response.get("endToEnd", False),
            supports_webchat=api_response.get("supportsWebchat", False),
            supports_temperature=api_response.get("supportsTemperature", False),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.model_id,
            "name": self.name,
            "polyaiModel": self.poly_ai_model,
            "providerModelId": self.provider_model_id,
            "endToEnd": self.speech_native,
            "supportsWebchat": self.supports_webchat,
            "supportsTemperature": self.supports_temperature,
        }


@dataclass
class Library:
    """Library model for PolyAI models."""

    last_refreshed: datetime
    region: str
    asr_models: list[ASRModel]
    llm_models: list[LLMModel]

    @classmethod
    def build_library(
        cls, region: str, asr_models: list[dict], llm_models: list[dict]
    ) -> "Library":
        # Load a library object from API responses
        return cls(
            last_refreshed=datetime.now(tz=timezone.utc),
            region=region,
            asr_models=[ASRModel.from_api_response(asr) for asr in asr_models],
            llm_models=[LLMModel.from_api_response(llm) for llm in llm_models],
        )

    @classmethod
    def load_library_from_file(cls, region: str) -> "Library":
        # Load library in ~/.poly/library/{region}.json
        import json
        import os

        library_path = os.path.join(LIBRARY_DIR, f"{region}.json")
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    asr_models = [ASRModel(**asr) for asr in data.get("asr_models", [])]
                    llm_models = [LLMModel(**llm) for llm in data.get("llm_models", [])]
                    return cls(
                        last_refreshed=datetime.fromisoformat(data.get("last_refreshed")),
                        region=region,
                        asr_models=asr_models,
                        llm_models=llm_models,
                    )
            except Exception as e:
                raise ValueError(f"Error loading library file: {library_path}") from e
        raise FileNotFoundError(f"Library for region '{region}' not found.")

    def save_library(self) -> None:
        # Save library in ~/.poly/library/{region}.json
        import json
        import os

        os.makedirs(LIBRARY_DIR, exist_ok=True)
        library_path = os.path.join(LIBRARY_DIR, f"{self.region}.json")
        with open(library_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_refreshed": self.last_refreshed.isoformat(),
                    "region": self.region,
                    "asr_models": [asdict(asr_model) for asr_model in self.asr_models],
                    "llm_models": [asdict(llm_model) for llm_model in self.llm_models],
                },
                f,
                indent=4,
            )

    def get_asr_model_by_id(self, model_id: str) -> ASRModel | None:
        for asr_model in self.asr_models:
            if asr_model.model_id == model_id:
                return asr_model
        return None

    def get_asr_model_by_name(self, name: str) -> ASRModel | None:
        for asr_model in self.asr_models:
            if asr_model.name == name:
                return asr_model
        return None

    def get_asr_model_by_provider_and_model(self, provider: str, model: str) -> ASRModel | None:
        for asr_model in self.asr_models:
            if asr_model.provider == provider and asr_model.model == model:
                return asr_model
        return None

    def get_llm_model_by_id(self, model_id: str) -> LLMModel | None:
        for llm_model in self.llm_models:
            if llm_model.model_id == model_id:
                return llm_model
        return None

    def get_llm_model_by_provider_model_id(self, provider_model_id: str) -> LLMModel | None:
        for llm_model in self.llm_models:
            if llm_model.provider_model_id == provider_model_id:
                return llm_model
        return None

    def get_llm_model_by_name(self, name: str) -> LLMModel | None:
        for llm_model in self.llm_models:
            if llm_model.name == name:
                return llm_model
        return None
