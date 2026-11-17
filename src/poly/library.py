"""Library module for PolyAI models."""

from dataclasses import dataclass


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


@dataclass
class LLMModel:
    """Library model for LLMs."""

    model_id: str
    name: str
    provider_model_id: str
    speech_native: bool
    supports_webchat: bool
    supports_temperature: bool

    @classmethod
    def from_api_response(cls, api_response: dict) -> "LLMModel":
        return cls(
            model_id=api_response.get("id"),
            name=api_response.get("name"),
            provider_model_id=api_response.get("providerModelId"),
            speech_native=api_response.get("endToEnd", False),
            supports_webchat=api_response.get("supportsWebchat", False),
            supports_temperature=api_response.get("supportsTemperature", False),
        )


@dataclass
class Library:
    """Library model for PolyAI models."""

    region: str
    asr_models: list[ASRModel]
    llm_models: list[LLMModel]

    @classmethod
    def build_library(
        cls, region: str, asr_models: list[dict], llm_models: list[dict]
    ) -> "Library":
        # Load a library object from API responses
        return cls(
            region=region,
            asr_models=[ASRModel.from_api_response(asr) for asr in asr_models],
            llm_models=[LLMModel.from_api_response(llm) for llm in llm_models],
        )

    @classmethod
    def load_library_from_file(cls, region: str) -> "Library":
        # Load library in ~/.poly/library/{region}.json
        import json
        import os

        library_dir = os.path.expanduser("~/.poly/library")
        library_path = os.path.join(library_dir, f"{region}.json")
        if os.path.exists(library_path):
            try:
                with open(library_path, "r") as f:
                    data = json.load(f)
                    asr_models = [ASRModel(**asr) for asr in data.get("asr_models", [])]
                    llm_models = [LLMModel(**llm) for llm in data.get("llm_models", [])]
                    return cls(region=region, asr_models=asr_models, llm_models=llm_models)
            except Exception as e:
                raise ValueError(f"Error loading library file: {library_path}") from e
        raise FileNotFoundError(f"Library for region '{region}' not found.")

    def save_library(self) -> None:
        # Save library in ~/.poly/library/{region}.json
        import json
        import os

        library_dir = os.path.expanduser("~/.poly/library")
        os.makedirs(library_dir, exist_ok=True)
        library_path = os.path.join(library_dir, f"{self.region}.json")
        with open(library_path, "w") as f:
            json.dump(
                {
                    "region": self.region,
                    "asr_models": [asr_model.__dict__ for asr_model in self.asr_models],
                    "llm_models": [llm_model.__dict__ for llm_model in self.llm_models],
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
