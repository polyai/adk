"""Tests for the local copy of the platform's model lists.

Copyright PolyAI Limited
"""

import os
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import poly.library
from poly.library import REFRESH_INTERVAL, ASRModel, Library, LLMModel

ASR_RESPONSE = [
    {"id": "ASR-1", "name": "Deepgram Nova 3", "provider": "deepgram", "model": "nova-3"},
    {"id": "ASR-2", "name": "Auto", "provider": "default", "model": "poly-latency"},
]

LLM_RESPONSE = [
    {
        "id": "MODEL-1",
        "name": "PolyAI Raven 3.5",
        "providerModelId": "polywhirl-3-5",
        "endToEnd": False,
        "polyaiModel": True,
        "supportsWebchat": True,
        "supportsTemperature": True,
    },
    {"id": "MODEL-2", "name": "Dialog-RSN-1", "providerModelId": "raven-omni", "endToEnd": True},
]


def patch_model_lists(asr_models=None, llm_models=None):
    """Patch the two list routes at the API boundary.

    Returns the ASR and language model patchers, already started; stop them with
    patch.stopall().
    """
    asr = patch(
        "poly.handlers.interface.AgentStudioInterface.get_asr_models",
        return_value=ASR_RESPONSE if asr_models is None else asr_models,
    ).start()
    llm = patch(
        "poly.handlers.interface.AgentStudioInterface.get_llm_models",
        return_value=LLM_RESPONSE if llm_models is None else llm_models,
    ).start()
    return asr, llm


def make_library(region: str = "us-1") -> Library:
    """Build a library from sample API responses."""
    return Library.build_library(region, ASR_RESPONSE, LLM_RESPONSE)


class BuildLibraryTest(unittest.TestCase):
    """Tests for building a library from the list routes' responses."""

    def test_asr_fields_are_read_from_the_response(self):
        """Each ASR record keeps its ID, name, provider and model."""
        library = make_library()

        self.assertEqual(
            library.asr_models[0],
            ASRModel(model_id="ASR-1", name="Deepgram Nova 3", provider="deepgram", model="nova-3"),
        )

    def test_llm_fields_are_mapped_to_snake_case(self):
        """Language model flags come from the route's camelCase fields."""
        model = make_library().llm_models[0]

        self.assertEqual(model.model_id, "MODEL-1")
        self.assertEqual(model.provider_model_id, "polywhirl-3-5")
        self.assertFalse(model.speech_native)
        self.assertTrue(model.supports_webchat)
        self.assertTrue(model.supports_temperature)

    def test_missing_llm_flags_default_to_false(self):
        """A record without a capability flag reads as not supporting it."""
        model = make_library().llm_models[1]

        self.assertTrue(model.speech_native)
        self.assertFalse(model.supports_webchat)
        self.assertFalse(model.supports_temperature)

    def test_region_and_refresh_time_are_recorded(self):
        """The library remembers its region and when it was built."""
        before = datetime.now(UTC)
        library = make_library("euw-1")

        self.assertEqual(library.region, "euw-1")
        self.assertGreaterEqual(library.last_refreshed, before)


class LibraryFileTest(unittest.TestCase):
    """Tests for saving and loading the library under the library directory."""

    def test_save_then_load_round_trips(self):
        """A saved library loads back with the same models and refresh time."""
        library = make_library()
        library.save_library()

        loaded = Library.load_library_from_file("us-1")

        self.assertEqual(loaded, library)

    def test_each_region_is_saved_to_its_own_file(self):
        """Libraries for different regions don't overwrite each other."""
        make_library("us-1").save_library()
        make_library("euw-1").save_library()

        self.assertTrue(os.path.exists(os.path.join(poly.library.LIBRARY_DIR, "us-1.json")))
        self.assertTrue(os.path.exists(os.path.join(poly.library.LIBRARY_DIR, "euw-1.json")))

    def test_missing_file_raises_file_not_found(self):
        """A region with no saved library raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            Library.load_library_from_file("uk-1")

    def test_corrupt_file_raises_value_error(self):
        """An unreadable library file raises ValueError naming the file."""
        os.makedirs(poly.library.LIBRARY_DIR, exist_ok=True)
        with open(os.path.join(poly.library.LIBRARY_DIR, "us-1.json"), "w") as f:
            f.write("{not json")

        with self.assertRaises(ValueError) as ctx:
            Library.load_library_from_file("us-1")

        self.assertIn("us-1.json", str(ctx.exception))


class LibraryLookupTest(unittest.TestCase):
    """Tests for finding models in the library."""

    def setUp(self):
        self.library = make_library()

    def test_asr_lookups_find_the_same_model(self):
        """An ASR model is found by its ID, its name, and its provider and model."""
        by_id = self.library.get_asr_model_by_id("ASR-1")

        self.assertEqual(by_id.name, "Deepgram Nova 3")
        self.assertIs(self.library.get_asr_model_by_name("Deepgram Nova 3"), by_id)
        self.assertIs(
            self.library.get_asr_model_by_provider_and_model("deepgram", "nova-3"), by_id
        )

    def test_llm_lookups_find_the_same_model(self):
        """A language model is found by its ID, its name, and its provider model ID."""
        by_id = self.library.get_llm_model_by_id("MODEL-1")

        self.assertEqual(by_id.name, "PolyAI Raven 3.5")
        self.assertIs(self.library.get_llm_model_by_name("PolyAI Raven 3.5"), by_id)
        self.assertIs(self.library.get_llm_model_by_provider_model_id("polywhirl-3-5"), by_id)

    def test_unknown_values_return_none(self):
        """Every lookup returns None for a value the library doesn't hold."""
        self.assertIsNone(self.library.get_asr_model_by_id("ASR-404"))
        self.assertIsNone(self.library.get_asr_model_by_name("Missing"))
        self.assertIsNone(self.library.get_asr_model_by_provider_and_model("deepgram", "nova-9"))
        self.assertIsNone(self.library.get_llm_model_by_id("MODEL-404"))
        self.assertIsNone(self.library.get_llm_model_by_name("Missing"))
        self.assertIsNone(self.library.get_llm_model_by_provider_model_id("gpt-0"))

    def test_asr_provider_and_model_must_both_match(self):
        """A model ID under a different provider isn't a match."""
        self.assertIsNone(self.library.get_asr_model_by_provider_and_model("openai", "nova-3"))


class LibraryStalenessTest(unittest.TestCase):
    """Tests for when a saved library counts as out of date."""

    def _library_aged(self, age: timedelta) -> Library:
        library = make_library()
        library.last_refreshed = datetime.now(UTC) - age
        return library

    def test_library_within_the_interval_is_fresh(self):
        """A library younger than REFRESH_INTERVAL isn't stale."""
        self.assertFalse(self._library_aged(REFRESH_INTERVAL - timedelta(minutes=1)).is_stale)

    def test_library_past_the_interval_is_stale(self):
        """A library older than REFRESH_INTERVAL is stale."""
        self.assertTrue(self._library_aged(REFRESH_INTERVAL + timedelta(minutes=1)).is_stale)

    def test_new_library_is_fresh(self):
        """A library built just now isn't stale."""
        self.assertFalse(make_library().is_stale)


class RefreshLibraryTest(unittest.TestCase):
    """Tests for Library.load_library_from_api, which fetches both lists and saves them."""

    def setUp(self):
        self.mock_asr, self.mock_llm = patch_model_lists()

    def tearDown(self):
        patch.stopall()

    def test_fetches_both_lists_for_the_region(self):
        """Both list routes are called once, for the given region."""
        Library.load_library_from_api("euw-1")

        self.mock_asr.assert_called_once_with("euw-1")
        self.mock_llm.assert_called_once_with("euw-1")

    def test_returns_and_saves_the_new_library(self):
        """The fetched library is returned and saved for its region."""
        library = Library.load_library_from_api("euw-1")

        self.assertEqual(len(library.asr_models), len(ASR_RESPONSE))
        self.assertEqual(len(library.llm_models), len(LLM_RESPONSE))
        self.assertEqual(Library.load_library_from_file("euw-1"), library)

    def test_given_api_handler_is_used_instead_of_the_default(self):
        """A caller's own handler fetches the lists, and the default isn't touched."""
        handler = MagicMock()
        handler.get_asr_models.return_value = ASR_RESPONSE[:1]
        handler.get_llm_models.return_value = []

        library = Library.load_library_from_api("euw-1", handler)

        handler.get_asr_models.assert_called_once_with("euw-1")
        self.mock_asr.assert_not_called()
        self.assertEqual(len(library.asr_models), 1)

    def test_overwrites_an_older_saved_library(self):
        """Refreshing replaces what was saved before for that region."""
        Library.build_library("euw-1", [], []).save_library()

        Library.load_library_from_api("euw-1")

        self.assertEqual(len(Library.load_library_from_file("euw-1").asr_models), len(ASR_RESPONSE))


class LLMModelTest(unittest.TestCase):
    """Tests for LLMModel on its own."""

    def test_to_dict_returns_the_route_shape(self):
        """to_dict gives back the route's camelCase record, including polyaiModel."""
        self.assertEqual(
            LLMModel.from_api_response(LLM_RESPONSE[0]).to_dict(),
            {key: value for key, value in LLM_RESPONSE[0].items()},
        )

    def test_asr_to_dict_returns_the_route_shape(self):
        """ASRModel.to_dict gives back the route's record."""
        self.assertEqual(ASRModel.from_api_response(ASR_RESPONSE[0]).to_dict(), ASR_RESPONSE[0])

    def test_from_api_response_ignores_unknown_fields(self):
        """Fields the ADK doesn't use, such as polyaiModel, don't break parsing."""
        model = LLMModel.from_api_response(LLM_RESPONSE[0])

        self.assertEqual(model.name, "PolyAI Raven 3.5")
