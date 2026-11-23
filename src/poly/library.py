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
class TTSVoice:
    """Library model for TTS voices."""

    voice_id: str
    name: str
    provider: str
    provider_voice_id: str
    config: dict
    metadata: dict
    poly_ai_voice: bool

    @classmethod
    def from_api_response(cls, api_response: dict) -> "TTSVoice":
        return cls(
            voice_id=api_response.get("id"),
            name=api_response.get("name"),
            provider=api_response.get("provider"),
            provider_voice_id=api_response.get("providerVoiceId"),
            config=api_response.get("config", {}),
            metadata=api_response.get("metadata", {}),
            poly_ai_voice=api_response.get("isPolyVoice", False),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.voice_id,
            "name": self.name,
            "provider": self.provider,
            "providerVoiceId": self.provider_voice_id,
            "config": self.config,
            "metadata": self.metadata,
            "isPolyVoice": self.poly_ai_voice,
        }


@dataclass
class Library:
    """Library model for PolyAI models."""

    last_refreshed: datetime
    region: str
    asr_models: list[ASRModel]
    llm_models: list[LLMModel]
    tts_voices: list[TTSVoice]
    account_id: Optional[str] = None

    @property
    def is_stale(self) -> bool:
        """Whether the library is stale and needs to be refreshed."""
        return datetime.now(timezone.utc) - self.last_refreshed > REFRESH_INTERVAL

    @classmethod
    def load_library_from_api(
        cls,
        region: str,
        account_id: Optional[str] = None,
        api_handler: Optional["AgentStudioInterface"] = None,
    ) -> "Library":
        """Load the library of models for the specified region from the API

        Args:
            region (str): The region to refresh the library for.
            account_id (Optional[str], optional): The account ID to use for fetching models. Defaults to None. If not provided, will not load TTS voices.
            api_handler (optional): The API handler to use for fetching models.
            Defaults to None, which uses AgentStudioInterface.

        Returns:
            Library: The refreshed library object.
        """
        if api_handler is None:
            from poly.handlers.interface import AgentStudioInterface

            api_handler = AgentStudioInterface

        # Load the latest ASR and LLM async models and build the library
        with ThreadPoolExecutor(max_workers=3) as executor:
            asr_future = executor.submit(api_handler.get_asr_models, region)
            llm_future = executor.submit(api_handler.get_llm_models, region)
            if account_id is not None:
                tts_future = executor.submit(api_handler.get_tts_voices, region, account_id)
            asr_models = asr_future.result()
            llm_models = llm_future.result()
            if account_id is not None:
                tts_voices = tts_future.result()

        library = cls.build_library(
            region,
            asr_models,
            llm_models,
            tts_voices if account_id is not None else [],
            account_id=account_id,
        )
        library.save_library()
        return library

    @classmethod
    def build_library(
        cls,
        region: str,
        asr_models: list[dict],
        llm_models: list[dict],
        tts_voices: list[dict],
        account_id: Optional[str] = None,
    ) -> "Library":
        # Load a library object from API responses
        return cls(
            last_refreshed=datetime.now(tz=timezone.utc),
            region=region,
            asr_models=[ASRModel.from_api_response(asr) for asr in asr_models],
            llm_models=[LLMModel.from_api_response(llm) for llm in llm_models],
            tts_voices=[TTSVoice.from_api_response(tts) for tts in tts_voices],
            account_id=account_id,
        )

    @classmethod
    def load_library_from_file(cls, region: str, account_id: Optional[str] = None) -> "Library":
        # Load library in ~/.poly/library/{region}.json

        library_path = os.path.join(LIBRARY_DIR, f"{region}.json")
        tts_voices: list[TTSVoice] = []
        tts_last_refreshed: Optional[datetime] = None
        if account_id is not None:
            tts_library_path = os.path.join(LIBRARY_DIR, f"{region}-{account_id}.json")
            if os.path.exists(tts_library_path):
                try:
                    with open(tts_library_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        tts_last_refreshed = datetime.fromisoformat(data.get("last_refreshed"))
                        tts_voices = [TTSVoice(**tts) for tts in data.get("tts_voices", [])]
                except Exception as e:
                    raise ValueError(f"Error loading TTS library file: {tts_library_path}") from e
        if os.path.exists(library_path):
            try:
                with open(library_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    asr_models = [ASRModel(**asr) for asr in data.get("asr_models", [])]
                    llm_models = [LLMModel(**llm) for llm in data.get("llm_models", [])]
                    last_refreshed = datetime.fromisoformat(data.get("last_refreshed"))
                    if tts_last_refreshed is not None:
                        last_refreshed = max(last_refreshed, tts_last_refreshed)
                    return cls(
                        last_refreshed=last_refreshed,
                        region=region,
                        asr_models=asr_models,
                        llm_models=llm_models,
                        tts_voices=tts_voices,
                        account_id=account_id,
                    )
            except Exception as e:
                raise ValueError(f"Error loading library file: {library_path}") from e
        raise FileNotFoundError(f"Library for region '{region}' not found.")

    def save_library(self) -> None:
        # Save ASR, LLM library in ~/.poly/library/{region}.json
        # Save TTS voices in ~/.poly/library/{region}-{account_id}.json
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
        if self.account_id is not None:
            tts_library_path = os.path.join(LIBRARY_DIR, f"{self.region}-{self.account_id}.json")
            with open(tts_library_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "last_refreshed": self.last_refreshed.isoformat(),
                        "tts_voices": [asdict(tts_voice) for tts_voice in self.tts_voices],
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

    def get_tts_voice_by_name(self, name: str) -> TTSVoice | None:
        if not name:
            return None
        for tts_voice in self.tts_voices:
            if tts_voice.name.strip().lower() == name.strip().lower():
                return tts_voice
        return None

    def get_tts_voice_by_id(self, voice_id: str) -> TTSVoice | None:
        if not voice_id:
            return None
        for tts_voice in self.tts_voices:
            if tts_voice.voice_id.strip().lower() == voice_id.strip().lower():
                return tts_voice
        return None
