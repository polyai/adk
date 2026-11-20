"""Library module for PolyAI models."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from poly.constants import POLY_HOME_DIR

if TYPE_CHECKING:
    from poly.handlers.interface import AgentStudioInterface

LIBRARY_DIR = os.path.join(POLY_HOME_DIR, "library")
REFRESH_INTERVAL = timedelta(days=1)


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
    poly_ai_model: bool
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

    @property
    def is_stale(self) -> bool:
        """Whether the library is stale and needs to be refreshed."""
        return datetime.now(timezone.utc) - self.last_refreshed > REFRESH_INTERVAL

    @classmethod
    def load_library_from_api(
        cls, region: str, api_handler: Optional["AgentStudioInterface"] = None
    ) -> "Library":
        """Load the library of models for the specified region from the API

        Args:
            region (str): The region to refresh the library for.
            api_handler (optional): The API handler to use for fetching models.
            Defaults to None, which uses AgentStudioInterface.

        Returns:
            Library: The refreshed library object.
        """
        if api_handler is None:
            from poly.handlers.interface import AgentStudioInterface

            api_handler = AgentStudioInterface

        # Load the latest ASR and LLM async models and build the library
        with ThreadPoolExecutor(max_workers=2) as executor:
            asr_future = executor.submit(api_handler.get_asr_models, region)
            llm_future = executor.submit(api_handler.get_llm_models, region)
            asr_models = asr_future.result()
            llm_models = llm_future.result()

        library = cls.build_library(region, asr_models, llm_models)
        library.save_library()
        return library

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
        if not name:
            return None
        for asr_model in self.asr_models:
            if asr_model.name.strip().lower() == name.strip().lower():
                return asr_model
        return None

    def get_asr_model_by_provider_and_model(self, provider: str, model: str) -> ASRModel | None:
        if not provider or not model:
            return None
        for asr_model in self.asr_models:
            if (
                asr_model.provider.strip().lower() == provider.strip().lower()
                and asr_model.model.strip().lower() == model.strip().lower()
            ):
                return asr_model
        return None

    def get_llm_model_by_id(self, model_id: str) -> LLMModel | None:
        for llm_model in self.llm_models:
            if llm_model.model_id == model_id:
                return llm_model
        return None

    def get_llm_model_by_provider_model_id(self, provider_model_id: str) -> LLMModel | None:
        if not provider_model_id:
            return None
        for llm_model in self.llm_models:
            if llm_model.provider_model_id.strip().lower() == provider_model_id.strip().lower():
                return llm_model
        return None

    def get_llm_model_by_name(self, name: str) -> LLMModel | None:
        if not name:
            return None
        for llm_model in self.llm_models:
            if llm_model.name.strip().lower() == name.strip().lower():
                return llm_model
        return None
