"""Sync client for Agent Studio content management

Copyright PolyAI Limited
"""

import logging
import uuid
from copy import deepcopy
from typing import Any, Optional

from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.protobuf.handoff_pb2 import Handoff_SetDefault
from poly.handlers.sdk import SourcererAPIError, SourcererSDK
from poly.resources import (
    ApiIntegration,
    ApiIntegrationEnvironments,
    ApiIntegrationOperation,
    ASRBiasing,
    AsrSettings,
    BaseResource,
    ChatGreeting,
    ChatSafetyFilters,
    ChatStylePrompt,
    parse_categories_from_azure_config,
    Condition,
    DTMFConfig,
    Entity,
    ExperimentalConfig,
    FlowConfig,
    FlowStep,
    Function,
    FunctionDelayResponse,
    FunctionLatencyControl,
    FunctionParameters,
    FunctionStep,
    FunctionType,
    Handoff,
    KeyphraseBoosting,
    PhraseFilter,
    Pronunciation,
    RegularExpressionRule,
    Resource,
    GeneralSafetyFilters,
    SettingsPersonality,
    SettingsRole,
    SettingsRules,
    SMSTemplate,
    Topic,
    TranscriptCorrection,
    Variable,
    Variant,
    VariantAttribute,
    VoiceDisclaimerMessage,
    VoiceGreeting,
    VoiceSafetyFilters,
    VoiceStylePrompt,
)

logger = logging.getLogger(__name__)

ROLE = "role"
PERSONALITY = "personality"
RULES = "rules"


class SyncClientHandler:
    """Sync client for Agent Studio content management"""

    region_to_region_env = {
        "euw-1": ("euw", "prod"),
        "uk-1": ("uk", "prod"),
        "us-1": ("us", "prod"),
        "staging": ("us", "staging"),
        "dev": ("us", "dev"),
    }

    _sdk: Optional[SourcererSDK] = None
    region: str
    account_id: str
    project_id: str

    @property
    def branch_id(self) -> str:
        """Get the current branch ID."""
        return self._sdk.branch_id

    def __init__(
        self,
        region: str,
        account_id: str,
        project_id: str,
        branch_id: Optional[str] = None,
    ):
        region_env = SyncClientHandler.region_to_region_env.get(region)
        if not region_env:
            raise ValueError(f"Unsupported region: {region}")

        self.region = region
        self.account_id = account_id
        self.project_id = project_id

        self._sdk = SourcererSDK(
            region=region_env[0],
            environment=region_env[1],
            account_id=account_id,
            project_id=project_id,
            branch_id=branch_id,
        )

    @property
    def sdk(self) -> SourcererSDK:
        """Get the Sourcerer SDK instance."""
        return self._sdk

    def assert_branch_exists(self) -> str:
        """Assert that the branch exists and switch to 'main' if it doesn't."""
        if self.branch_id != "main":
            found_branches = self._sdk.fetch_branches().get("branches", [])
            branch = next((b for b in found_branches if b.get("branchId") == self.branch_id), None)
            if not branch:
                logger.info(
                    f"Branch ID:'{self.branch_id}' does not exist. Switching to 'main' branch."
                )
                self._sdk.branch_id = "main"
        return self.branch_id

    @classmethod
    def load_resources_from_projection(
        cls, projection: dict
    ) -> dict[type[Resource], dict[str, Resource]]:
        return {
            Topic: cls._read_topics_from_projection(projection),
            Function: cls._read_functions_from_projection(projection),
            Entity: cls._read_entities_from_projection(projection),
            Variable: cls._read_variables_from_projection(projection),
            **cls._read_agent_settings_from_projection(projection),
            **cls._read_channel_settings_from_projection(projection),
            **cls._read_flows_from_projection(projection),
            ExperimentalConfig: cls._read_experimental_config_from_projection(projection),
            SMSTemplate: cls._read_sms_templates_from_projection(projection),
            Handoff: cls._read_handoffs_from_projection(projection),
            **cls._read_variants_from_projection(projection),
            PhraseFilter: cls._read_phrase_filters_from_projection(projection),
            Pronunciation: cls._read_pronunciations_from_projection(projection),
            KeyphraseBoosting: cls._read_keyphrase_boosting_from_projection(projection),
            TranscriptCorrection: cls._read_transcript_corrections_from_projection(projection),
            **cls._read_asr_settings_from_projection(projection),
            GeneralSafetyFilters: cls._read_safety_filters_from_projection(projection),
            ApiIntegration: cls._read_api_integrations_from_projection(projection),
        }  # ty:ignore[invalid-return-type]

    def pull_deployment_resources(
        self, deployment_id: str
    ) -> dict[type[Resource], dict[str, Resource]]:
        """Fetch all resources for a specific deployment of a project.
        Args:
            deployment_id (str): The deployment ID
        Returns:
            dict[type[Resource], dict[str, Resource]]: A dictionary mapping resource types to
                their resources
        """
        logger.info(
            f"Fetching project data for project {self.project_id} for deployment {deployment_id}"
        )
        self.assert_branch_exists()
        projection = self.sdk.fetch_deployment_projection(deployment_id=deployment_id)
        logger.info(
            f"Successfully fetched project data for project {self.project_id} for deployment {deployment_id}"
        )
        return self.load_resources_from_projection(projection)

    def pull_resources(self) -> tuple[dict[type[Resource], dict[str, Resource]], dict[str, Any]]:
        """Fetch all resources from a specific project.

        Returns:
            dict[type[Resource], dict[str, Resource]]: A dictionary mapping resource types to
                their resources
            dict[str, Any]: The projection data
        """
        logger.info(
            f"Fetching project data for project {self.project_id} on branch {self.sdk.branch_id}"
        )
        self.assert_branch_exists()
        projection = self.sdk.fetch_projection(force_refresh=True)
        logger.debug(f"Projection: {projection}")
        logger.info(
            f"Successfully fetched project data for project {self.project_id} on branch {self.sdk.branch_id}"
        )
        return self.load_resources_from_projection(projection), projection

    @staticmethod
    def _read_topics_from_projection(projection: dict) -> dict[str, Topic]:
        topics = {}
        for topic_id, topic in (
            projection.get("knowledgeBase", {}).get("topics", {}).get("entities", {}).items()
        ):
            example_queries = topic.get("exampleQueries", [])
            queries = [
                example_queries["query"]
                for example_queries in example_queries
                if "query" in example_queries
            ]
            topics[topic_id] = Topic(
                resource_id=topic_id,
                name=topic["name"],
                actions=topic["actions"],
                content=topic["content"],
                example_queries=queries,
                enabled=topic.get("isActive", True),
            )

        return topics

    @staticmethod
    def _parse_latency_control(latency_control_data: dict) -> FunctionLatencyControl:
        """Parse latency control from a projection dictionary."""
        if not latency_control_data:
            return FunctionLatencyControl()

        delay_responses = latency_control_data.get(
            "delayResponses", latency_control_data.get("delay_responses", {})
        )
        if isinstance(delay_responses, dict):
            delay_responses = list(
                delay_responses.get("entities", delay_responses).values()
                if "entities" in delay_responses
                else delay_responses.values()
            )

        delay_responses = [
            FunctionDelayResponse(
                id=delay_response.get("id"),
                message=delay_response.get("message", ""),
                duration=delay_response.get("duration", 0),
            )
            for delay_response in delay_responses
            if isinstance(delay_response, dict)
        ]

        return FunctionLatencyControl(
            enabled=latency_control_data.get("enabled", False),
            initial_delay=latency_control_data.get(
                "initialDelay", latency_control_data.get("initial_delay", 0)
            ),
            interval=latency_control_data.get("interval", 0),
            delay_responses=delay_responses,
        )

    @staticmethod
    def _read_functions_from_projection(projection: dict) -> dict[str, Function]:
        functions = {}
        # Read special functions
        special_functions = projection.get("specialFunctions", {})
        for func_type, func in special_functions.items():
            if func.get("archived", False):
                continue

            if func_type == "startFunction":
                func_type = FunctionType.START

            if func_type == "endFunction":
                func_type = FunctionType.END

            functions[func["id"]] = Function(
                resource_id=func["id"],
                name=func["name"],
                description=func["description"],
                code=func["code"],
                parameters=[
                    FunctionParameters(
                        name=parameter.get("name"),
                        type=parameter.get("type"),
                        id=parameter.get("id"),
                        description=parameter.get("description"),
                    )
                    for parameter in func.get("parameters", {}).get("entities", {}).values()
                ],
                latency_control=SyncClientHandler._parse_latency_control(
                    func.get("latencyControl", func.get("latency_control"))
                ),
                flow_id=None,
                function_type=func_type,
            )

        # Read flow functions
        flows = projection.get("flows", {}).get("flows", {}).get("entities", {})
        for flow_id, flow_data in flows.items():
            for func_id, func in (
                flow_data.get("transitionFunctions", {}).get("entities", {}).items()
            ):
                if func.get("archived", False):
                    continue

                functions[func_id] = Function(
                    resource_id=func_id,
                    name=func["name"],
                    description=func["description"],
                    code=func["code"],
                    parameters=[
                        FunctionParameters(
                            name=parameter.get("name"),
                            type=parameter.get("type"),
                            id=parameter.get("id"),
                            description=parameter.get("description"),
                        )
                        for parameter in func.get("parameters", {}).get("entities", {}).values()
                    ],
                    latency_control=SyncClientHandler._parse_latency_control(
                        func.get("latencyControl", func.get("latency_control"))
                    ),
                    flow_id=flow_id,
                    flow_name=flow_data["name"],
                    function_type=FunctionType.TRANSITION,
                )

        # Read regular functions
        for func_id, func in (
            projection.get("functions", {}).get("functions", {}).get("entities", {}).items()
        ):
            if func.get("archived", False):
                continue

            functions[func_id] = Function(
                resource_id=func_id,
                name=func["name"],
                description=func["description"],
                code=func["code"],
                parameters=[
                    FunctionParameters(
                        name=parameter.get("name"),
                        type=parameter.get("type"),
                        id=parameter.get("id"),
                        description=parameter.get("description"),
                    )
                    for parameter in func.get("parameters", {}).get("entities", {}).values()
                ],
                latency_control=SyncClientHandler._parse_latency_control(
                    func.get("latencyControl", func.get("latency_control"))
                ),
                flow_id=None,
                function_type=FunctionType.GLOBAL,
            )

        return functions

    @staticmethod
    def _read_agent_settings_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        settings = {}
        agent_settings = projection.get("agentSettings", {})
        if personality := agent_settings.get("personality", None):
            settings[SettingsPersonality] = {
                PERSONALITY: SettingsPersonality(
                    resource_id=PERSONALITY,
                    name=PERSONALITY,
                    adjectives=personality.get("adjectives", {}),
                    custom=personality.get("custom", ""),
                )
            }
        if role := agent_settings.get("role", None):
            settings[SettingsRole] = {
                ROLE: SettingsRole(
                    resource_id=ROLE,
                    name=ROLE,
                    value=role.get("value", ""),
                    additional_info=role.get("additionalInfo", ""),
                    custom=role.get("custom", ""),
                )
            }
        if rules := agent_settings.get("rules", None):
            settings[SettingsRules] = {
                RULES: SettingsRules(
                    resource_id=RULES,
                    name=RULES,
                    behaviour=rules.get("behaviour", ""),
                )
            }
        return settings

    @staticmethod
    def _read_channel_settings_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        settings = {}
        channels = projection.get("channels", {})

        voice_settings = channels.get("voice", {})
        voice_config = voice_settings.get("config", {}) or {}
        if voice_greeting := voice_config.get("greeting", None):
            settings[VoiceGreeting] = {
                "voice_greeting": VoiceGreeting(
                    resource_id="voice_greeting",
                    name="voice_greeting",
                    welcome_message=voice_greeting.get("welcomeMessage", ""),
                    language_code=voice_greeting.get("languageCode", "en-GB"),
                )
            }
        if voice_style_prompt := voice_config.get("stylePrompt", None):
            settings[VoiceStylePrompt] = {
                "voice_style_prompt": VoiceStylePrompt(
                    resource_id="voice_style_prompt",
                    name="voice_style_prompt",
                    prompt=voice_style_prompt.get("prompt", ""),
                )
            }
        if voice_safety_filters := voice_config.get("safetyFilters", None):
            azure = voice_safety_filters.get("azureConfig", {})
            settings[VoiceSafetyFilters] = {
                "voice_safety_filters": VoiceSafetyFilters(
                    resource_id="voice_safety_filters",
                    name="voice_safety_filters",
                    enabled=not voice_safety_filters.get("disabled", False),
                    filter_type=voice_safety_filters.get("type", "azure"),
                    categories=parse_categories_from_azure_config(azure),
                )
            }
        if voice_disclaimer := voice_settings.get("disclaimer", None):
            settings[VoiceDisclaimerMessage] = {
                "voice_disclaimer": VoiceDisclaimerMessage(
                    resource_id="voice_disclaimer",
                    name="voice_disclaimer",
                    message=voice_disclaimer.get("message", ""),
                    enabled=voice_disclaimer.get("enabled", False),
                    language_code=voice_disclaimer.get("languageCode", "en-GB"),
                )
            }

        web_chat_settings = channels.get("webChat", {})
        if not web_chat_settings.get("status", False):
            return settings

        chat_config = web_chat_settings.get("config", {}) or {}
        if chat_greeting := chat_config.get("greeting", None):
            settings[ChatGreeting] = {
                "chat_greeting": ChatGreeting(
                    resource_id="chat_greeting",
                    name="chat_greeting",
                    welcome_message=chat_greeting.get("welcomeMessage", ""),
                    language_code=chat_greeting.get("languageCode", "en-GB"),
                )
            }
        if chat_style_prompt := chat_config.get("stylePrompt", None):
            settings[ChatStylePrompt] = {
                "chat_style_prompt": ChatStylePrompt(
                    resource_id="chat_style_prompt",
                    name="chat_style_prompt",
                    prompt=chat_style_prompt.get("prompt", ""),
                )
            }
        if chat_safety_filters := chat_config.get("safetyFilters", None):
            azure = chat_safety_filters.get("azureConfig", {})
            settings[ChatSafetyFilters] = {
                "chat_safety_filters": ChatSafetyFilters(
                    resource_id="chat_safety_filters",
                    name="chat_safety_filters",
                    enabled=not chat_safety_filters.get("disabled", False),
                    filter_type=chat_safety_filters.get("type", "azure"),
                    categories=parse_categories_from_azure_config(azure),
                )
            }

        return settings

    @staticmethod
    def _read_entities_from_projection(
        projection: dict,
    ) -> dict[str, Entity]:
        entities = {}
        for entity_id, entity_data in (
            projection.get("entities", {}).get("entities", {}).get("entities", {}).items()
        ):
            entities[entity_id] = Entity(
                resource_id=entity_id,
                name=entity_data["name"],
                description=entity_data.get("description", ""),
                entity_type=entity_data.get("type"),
                config=entity_data.get("config", {}).get("value", {}),
            )
        return entities

    @staticmethod
    def _read_variables_from_projection(
        projection: dict,
    ) -> dict[str, Variable]:
        variables = {}
        variables_data = projection.get("variables", {}).get("variables", {}).get("entities", {})
        for var_id, var_data in variables_data.items():
            variables[var_id] = Variable(
                resource_id=var_id,
                name=var_data.get("name", ""),
            )

        return variables

    @staticmethod
    def _read_flows_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        resources: dict[type[Resource], dict[str, Resource]] = {}
        flows = projection.get("flows", {}).get("flows", {}).get("entities", {})

        for flow_id, flow_data in flows.items():
            resources.setdefault(FlowConfig, {})[flow_id] = FlowConfig(
                resource_id=flow_id,
                name=flow_data["name"],
                description=flow_data.get("description", ""),
                start_step=flow_data.get("startStepId", ""),
            )

            for step_id, step in flow_data.get("steps", {}).get("entities", {}).items():
                local_resource_id = f"{flow_data['name']}_{step_id}"

                if step.get("type") == "function_step":
                    function = step.get("function", {})
                    resources.setdefault(FunctionStep, {})[local_resource_id] = FunctionStep(
                        resource_id=local_resource_id,
                        step_id=step_id,
                        flow_id=flow_id,
                        flow_name=flow_data["name"],
                        name=step["name"],
                        position=step.get("position"),
                        code=function.get("code", ""),
                        latency_control=SyncClientHandler._parse_latency_control(
                            function.get("latencyControl", function.get("latency_control"))
                        ),
                        parameters=[],
                        function_id=function.get("id", ""),
                    )
                    continue

                asr_biasing_data = step.get("asrBiasing", {})
                dtmf_config_data = step.get("dtmfConfig", {})

                references = step.get("references", {})
                extracted_entities = list(references.get("extractedEntities", {}).keys())

                resources.setdefault(FlowStep, {})[local_resource_id] = FlowStep(
                    resource_id=local_resource_id,
                    step_id=step_id,
                    name=step["name"],
                    flow_id=flow_id,
                    flow_name=flow_data["name"],
                    step_type=step.get("type"),
                    asr_biasing=ASRBiasing(
                        alphanumeric=asr_biasing_data.get("alphanumeric", False),
                        name_spelling=asr_biasing_data.get("nameSpelling", False),
                        numeric=asr_biasing_data.get("numeric", False),
                        party_size=asr_biasing_data.get("partySize", False),
                        precise_date=asr_biasing_data.get("preciseDate", False),
                        relative_date=asr_biasing_data.get("relativeDate", False),
                        single_number=asr_biasing_data.get("singleNumber", False),
                        time=asr_biasing_data.get("time", False),
                        yes_no=asr_biasing_data.get("yesNo", False),
                        address=asr_biasing_data.get("address", False),
                        custom_keywords=asr_biasing_data.get("customKeywords", []),
                        is_enabled=asr_biasing_data.get("isEnabled", False),
                        step_id=step_id,
                        flow_id=flow_id,
                    ),
                    dtmf_config=DTMFConfig(
                        is_enabled=dtmf_config_data.get("isEnabled", False),
                        inter_digit_timeout=dtmf_config_data.get("interDigitTimeout", 0),
                        max_digits=dtmf_config_data.get("maxDigits", 0),
                        end_key=dtmf_config_data.get("endKey", ""),
                        collect_while_agent_speaking=dtmf_config_data.get(
                            "collectWhileAgentSpeaking", False
                        ),
                        is_pii=dtmf_config_data.get("isPii", False),
                        step_id=step_id,
                        flow_id=flow_id,
                    ),
                    prompt=step.get("prompt", ""),
                    conditions=[
                        Condition(
                            resource_id=condition_data["id"],
                            name=condition_data["config"]["value"]["details"]["label"],
                            condition_type=condition_data["config"]["$case"],
                            description=condition_data["config"]["value"]["details"].get(
                                "description", ""
                            ),
                            required_entities=condition_data["config"]["value"]["details"].get(
                                "requiredEntities", []
                            ),
                            child_step=condition_data["config"]["value"].get("childStepId", ""),
                            step_id=step_id,
                            flow_id=flow_id,
                            ingress=condition_data["config"]["value"]["details"].get(
                                "ingressPosition", "top"
                            ),
                            position=condition_data["config"]["value"]["details"].get(
                                "position", {"x": 0.0, "y": 0.0}
                            ),
                            exit_flow_position=condition_data["config"]["value"].get(
                                "exitFlowPosition", None
                            ),
                        )
                        for condition_data in step.get("conditions", [])
                    ],
                    position=step.get("position"),
                    extracted_entities=extracted_entities,
                )
        return resources

    @staticmethod
    def _read_experimental_config_from_projection(
        projection: dict,
    ) -> dict[str, ExperimentalConfig]:
        experimental_configs = (
            projection.get("experimentalConfig", {})
            .get("experimentalConfigs", {})
            .get("entities", {})
        )
        # Only get the default experimental config
        default_experimental_config = experimental_configs.get("default", {})
        return {
            "default": ExperimentalConfig(
                resource_id="default",
                name="experimental_config",
                config=default_experimental_config.get("features", {}),
            )
        }

    @staticmethod
    def _read_sms_templates_from_projection(
        projection: dict,
    ) -> dict[str, SMSTemplate]:
        sms_templates_projection = (
            projection.get("sms", {}).get("templates", {}).get("entities", {})
        )
        sms_templates = {}
        for sms_template_id, sms_template_data in sms_templates_projection.items():
            if not sms_template_data.get("active", False):
                continue
            sms_templates[sms_template_id] = SMSTemplate(
                resource_id=sms_template_id,
                name=sms_template_data["name"],
                text=sms_template_data.get("text", ""),
                env_phone_numbers=sms_template_data.get("envPhoneNumbers", {}),
            )
        return sms_templates

    @staticmethod
    def _read_handoffs_from_projection(
        projection: dict,
    ) -> dict[str, Handoff]:
        handoffs_projection = projection.get("handoff", {}).get("handoffs", {}).get("entities", {})
        handoffs = {}
        for handoff_id, handoff_data in handoffs_projection.items():
            if not handoff_data.get("active", False):
                continue

            config = handoff_data.get("sipConfig", {}).get("config", {})
            method = config.get("$case", "bye")
            value = config.get("value", {})

            sip_config = {"method": method}
            if method == "invite":
                sip_config["phone_number"] = value.get("phoneNumber", "")
                sip_config["outbound_endpoint"] = value.get("outboundEndpoint", "")
                sip_config["outbound_encryption"] = value.get("outboundEncryption", "")
            elif method == "refer":
                sip_config["phone_number"] = value.get("phoneNumber", "")

            sip_headers = handoff_data.get("sipHeaders", {}).get("headers", [])

            handoffs[handoff_id] = Handoff(
                resource_id=handoff_id,
                name=handoff_data.get("name", ""),
                description=handoff_data.get("description", ""),
                is_default=handoff_data.get("isDefault", False),
                sip_config=sip_config,
                sip_headers=sip_headers,
            )
        return handoffs

    @staticmethod
    def _read_variants_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        response = {}
        variants = {}
        for variant_id, variant_data in (
            projection.get("variantManagement", {}).get("variants", {}).get("entities", {}).items()
        ):
            variants[variant_id] = Variant(
                resource_id=variant_id,
                name=variant_data["name"],
                is_default=variant_data.get("isDefault", False),
            )
        if variants:
            response[Variant] = variants

        # variantAttributeValues: entities: dict[variant_id: dict[attribute_id: attribute_value]]
        # attributes: entities: dict[attribute_id: dict["name": name]
        variant_attributes = {}
        for attribute_id, attribute_data in (
            projection.get("variantManagement", {})
            .get("attributes", {})
            .get("entities", {})
            .items()
        ):
            if attribute_data["archived"]:
                continue
            variant_attributes[attribute_id] = VariantAttribute(
                resource_id=attribute_id, name=attribute_data["name"], mappings={}
            )
        if not variant_attributes:
            return response

        for variant_id, variant_attribute_values in (
            projection.get("variantManagement", {})
            .get("variantAttributeValues", {})
            .get("entities", {})
            .items()
        ):
            for attribute_id, attribute_value in variant_attribute_values.get("values", {}).items():
                if attribute_id in variant_attributes:
                    variant_attributes[attribute_id].mappings[variant_id] = attribute_value

        response[VariantAttribute] = variant_attributes

        return response

    @staticmethod
    def _read_phrase_filters_from_projection(
        projection: dict,
    ) -> dict[str, PhraseFilter]:
        phrase_filters = {}
        for filter_id, filter_data in (
            projection.get("stopKeywords", {}).get("filters", {}).get("entities", {}).items()
        ):
            references = filter_data.get("references", {})
            global_functions = references.get("globalFunctions", {})
            function_id = next(iter(global_functions), None) if global_functions else None

            phrase_filters[filter_id] = PhraseFilter(
                resource_id=filter_id,
                name=filter_data.get("title", ""),
                description=filter_data.get("description", ""),
                regular_expressions=filter_data.get("regularExpressions", []),
                say_phrase=filter_data.get("sayPhrase", False),
                language_code=filter_data.get("languageCode", ""),
                function=function_id,
            )
        return phrase_filters

    @staticmethod
    def _read_pronunciations_from_projection(
        projection: dict,
    ) -> dict[str, Pronunciation]:
        pronunciations = {}
        index = 0
        for pronunciation_id, pronunciation_data in (
            projection.get("pronunciations", {})
            .get("pronunciations", {})
            .get("entities", {})
            .items()
        ):
            # FIXME: Sourcerer SDK bug
            # Sometimes, even if the dict has multiple elements
            # They are all at position 0.
            position = pronunciation_data.get("position") or index
            pronunciations[pronunciation_id] = Pronunciation(
                resource_id=pronunciation_id,
                name=pronunciation_data.get("name", ""),
                regex=pronunciation_data.get("regex", ""),
                replacement=pronunciation_data.get("replacement", ""),
                case_sensitive=pronunciation_data.get("caseSensitive", False),
                language_code=pronunciation_data.get("languageCode", ""),
                description=pronunciation_data.get("description", ""),
                position=position if position == index else index + 1,
            )
            index += 1
        return pronunciations

    @staticmethod
    def _read_keyphrase_boosting_from_projection(
        projection: dict,
    ) -> dict[str, KeyphraseBoosting]:
        keyphrases = {}
        for kp_id, kp_data in (
            projection.get("keyphraseBoosting", {})
            .get("keyphraseBoosting", {})
            .get("entities", {})
            .items()
        ):
            # Names aren't a thing for keyphrase boosting
            keyphrases[kp_id] = KeyphraseBoosting(
                resource_id=kp_id,
                name=kp_data.get("keyphrase", ""),
                keyphrase=kp_data.get("keyphrase", ""),
                level=kp_data.get("level", "default"),
            )
        return keyphrases

    @staticmethod
    def _read_transcript_corrections_from_projection(
        projection: dict,
    ) -> dict[str, TranscriptCorrection]:
        corrections = {}
        for correction_id, correction_data in (
            projection.get("transcriptCorrections", {})
            .get("transcriptCorrections", {})
            .get("entities", {})
            .items()
        ):
            regular_expressions = [
                RegularExpressionRule(
                    regular_expression=r.get("regularExpression", ""),
                    replacement=r.get("replacement", ""),
                    replacement_type=r.get("replacementType", "full"),
                )
                for r in correction_data.get("regularExpressions", [])
            ]
            corrections[correction_id] = TranscriptCorrection(
                resource_id=correction_id,
                name=correction_data.get("name", ""),
                description=correction_data.get("description", ""),
                regular_expressions=regular_expressions,
            )
        return corrections

    @staticmethod
    def _read_asr_settings_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        asr_settings_data = projection.get("channels", {}).get("voice", {}).get("asrSettings", {})
        if not asr_settings_data:
            return {}

        barge_in = asr_settings_data.get("bargeIn", False)

        # Latency Config only has interaction style at this time
        interaction_style = asr_settings_data.get("latencyConfig", {}).get(
            "interactionStyle", "balanced"
        )

        return {
            AsrSettings: {
                "asr_settings": AsrSettings(
                    resource_id="asr_settings",
                    name="asr_settings",
                    barge_in=barge_in,
                    interaction_style=interaction_style,
                )
            }
        }

    @staticmethod
    def _read_safety_filters_from_projection(projection: dict) -> dict[str, GeneralSafetyFilters]:
        data = projection.get("contentFilterSettings", {})
        if not data:
            return {}
        azure = data.get("azureConfig", {})
        return {
            "safety_filters": GeneralSafetyFilters(
                resource_id="safety_filters",
                name="safety_filters",
                enabled=not data.get("disabled", False),
                filter_type=data.get("type", "azure"),
                categories=parse_categories_from_azure_config(azure),
            )
        }

    @staticmethod
    def _read_api_integrations_from_projection(
        projection: dict,
    ) -> dict[type[Resource], dict[str, Resource]]:
        api_integrations = {}
        for integration_id, integration_data in (
            projection.get("apiIntegrations", {})
            .get("apiIntegrations", {})
            .get("entities", {})
            .items()
        ):
            environments = ApiIntegrationEnvironments.from_dict(
                integration_data.get("environments")
            )
            operations_raw = integration_data.get("operations") or {}
            operations = [ApiIntegrationOperation.from_dict(v) for v in operations_raw.values()]

            api_integrations[integration_id] = ApiIntegration(
                resource_id=integration_id,
                name=integration_data.get("name", ""),
                description=integration_data.get("description", ""),
                environments=environments,
                operations=operations,
            )

        return api_integrations

    # Types that should be created first
    # as they are referenced by other resources
    PRIORITY_CREATE_TYPES = [
        # Things that are referenced in prompts
        Variable,
        Entity,
        Variant,
        VariantAttribute,
        SMSTemplate,
        Handoff,
        Function,
        # Steps should be created before conditions
        FlowConfig,  # Flow config contains initial steps and functions
        FunctionStep,
        FlowStep,
        Condition,
        # Integrations should be created before operations and environments
        ApiIntegration,
    ]

    PRIORITY_DELETE_TYPES = [
        # If a function is deleted and it is the last reference to a variable,
        # the variable will be deleted as well. So we need to delete variables
        # first or its delete command will fail.
        Variable,
        # Conditions should be deleted before steps, as steps auto delete their conditions
        Condition,
    ]

    PRIORITY_UPDATE_TYPES = [
        # If variable references will change, we should update the variable first so
        # it isn't pruned by the backend.
        Variable,
    ]

    def queue_resources(
        self,
        deleted_resources: dict[type[BaseResource], dict[str, BaseResource]],
        new_resources: dict[type[BaseResource], dict[str, BaseResource]],
        updated_resources: dict[type[BaseResource], dict[str, BaseResource]],
        email: Optional[str] = None,
    ) -> list[Command]:
        """Queue multiple resources for the specific project.

        Sends in order:
        - delete
        - create
        - update

        Args:
            deleted_resources (dict[type[BaseResource], dict[str, BaseResource]]): Resources to delete
            new_resources (dict[type[BaseResource], dict[str, BaseResource]]): New resources to upload
            updated_resources (dict[type[BaseResource], dict[str, BaseResource]]): Updated resources to upload
            email (str): Email to use for metadata creation.

        Returns:
            list[Command]: A list of queued Command protobuf messages.
        """
        metadata = self.sdk.create_metadata()
        if email:
            metadata.created_by = email

        commands = []

        delete_resources_priority: list[type[BaseResource]] = []
        for resource_type in self.PRIORITY_DELETE_TYPES:
            if resource_type in deleted_resources:
                delete_resources_priority.append(resource_type)
        for resource_type in deleted_resources.keys():
            if resource_type not in self.PRIORITY_DELETE_TYPES:
                delete_resources_priority.append(resource_type)

        for resource_type in delete_resources_priority:
            for resource_id, resource in deleted_resources.get(resource_type, {}).items():
                delete_type = resource.delete_command_type
                commands.append(
                    Command(
                        type=delete_type,
                        command_id=str(uuid.uuid4()),
                        metadata=metadata,
                        **{delete_type: resource.build_delete_proto()},
                    )
                )

        new_resources_priority: list[type[BaseResource]] = []
        for resource_type in self.PRIORITY_CREATE_TYPES:
            if resource_type in new_resources:
                new_resources_priority.append(resource_type)
        for resource_type in new_resources.keys():
            if resource_type not in self.PRIORITY_CREATE_TYPES:
                new_resources_priority.append(resource_type)

        for resource_type in new_resources_priority:
            resources = new_resources.get(resource_type, {})
            for resource_id, resource in resources.items():
                create_type = resource.create_command_type
                commands.append(
                    Command(
                        type=create_type,
                        command_id=str(uuid.uuid4()),
                        metadata=metadata,
                        **{create_type: resource.build_create_proto()},
                    )
                )

        updated_resource_priority: list[type[BaseResource]] = []
        for resource_type in self.PRIORITY_UPDATE_TYPES:
            if resource_type in updated_resources:
                updated_resource_priority.append(resource_type)
        for resource_type in updated_resources.keys():
            if resource_type not in self.PRIORITY_UPDATE_TYPES:
                updated_resource_priority.append(resource_type)

        for resource_type in updated_resource_priority:
            resources = updated_resources.get(resource_type, {})
            for resource_id, resource in resources.items():
                update_type = resource.update_command_type
                commands.append(
                    Command(
                        type=update_type,
                        command_id=str(uuid.uuid4()),
                        metadata=metadata,
                        **{update_type: resource.build_update_proto()},
                    )
                )

        # is_default is not part of create/update protos; it requires a separate command
        for resource_dict in [new_resources, updated_resources]:
            for resource_id, resource in resource_dict.get(Handoff, {}).items():
                if isinstance(resource, Handoff) and resource.is_default:
                    commands.append(
                        Command(
                            type="handoff_set_default",
                            command_id=str(uuid.uuid4()),
                            metadata=metadata,
                            handoff_set_default=Handoff_SetDefault(id=resource.resource_id),
                        )
                    )

        for command in commands:
            self.sdk.add_command_to_queue(command)

        logger.info(f"Queued {len(commands)} commands")
        logger.debug(f"Commands: {commands!r}")
        return commands

    def send_queued_commands(self) -> bool:
        """Send all queued commands as a batch and clear the queue.

        Returns:
            bool: True if the commands were sent successfully, False otherwise
        """
        if self.sdk.get_queue_size() == 0:
            logger.info("No commands to send")
            return True

        self.assert_branch_exists()

        # Creates branch and switches to it
        if self.sdk.branch_id == "main":
            self.create_branch()

        try:
            logger.info(f"Sending {len(self.sdk._command_queue)} commands to {self.sdk.branch_id}")
            self.sdk.send_command_batch()
            return True
        except SourcererAPIError as e:
            logger.error(f"Failed to send commands: {e}")
            return False

    def clear_command_queue(self) -> None:
        """Clear all queued commands without sending."""
        logger.info(f"Clearing {len(self.sdk._command_queue)} commands")
        self.sdk.clear_queue()

    def get_queued_commands(self) -> list[Command]:
        """Get all queued commands.

        Returns:
            list[Command]: A list of queued Command protobuf messages.
        """
        return deepcopy(self.sdk._command_queue)

    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different branch within the same project.

        Args:
            branch_id (str): The ID of the branch to switch to

        Returns:
            bool: True if the switch was successful, False otherwise
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == branch_id:
            logger.info(f"Already on branch ID:'{branch_id}'")
            return True

        if branch_id == "main":
            self.sdk.branch_id = "main"
            self.sdk.get_project_data()
            logger.info(f"Switched to branch ID:'{branch_id}'")
            return True

        if found_branches := self.sdk.fetch_branches().get("branches"):
            branch = next((b for b in found_branches if b.get("branchId") == branch_id), None)
            if branch:
                self.sdk.branch_id = branch_id
                # Re-fetch project data to ensure the SDK is up-to-date
                self.sdk.clear_cache()
                self.sdk.get_project_data()
                logger.info(f"Switched to branch ID:'{branch_id}'")
                return True
            else:
                logger.error(f"Branch ID:'{branch_id}' does not exist.")
                return False
        return False

    def create_branch(self, branch_name: Optional[str] = None) -> str:
        """Create a new branch for the project

        Args:
            branch_name: Optional name for the new branch. If not provided, a default name will be used.

        Returns:
            The ID of the created branch
        """
        self.sdk.branch_id = "main"
        self.sdk.get_project_data()

        if branch_name is None:
            metadata = self.sdk.create_metadata()
            time_suffix = f"{metadata.created_at.seconds % 100000:05d}"
            random_suffix = uuid.uuid4().hex[:4]
            suffix = f"{time_suffix}-{random_suffix}"  # to avoid duplicate names
            branch_name = f"ADK-{suffix}"

        logger.info(f"Creating new branch '{branch_name}' from 'main' branch")

        self.sdk.branch_id = self.sdk.create_branch(
            expected_main_last_known_sequence=self.sdk._last_known_sequence,
            branch_name=branch_name,
        )
        logger.info(
            f"Created and switched to new branch. Name:'{branch_name}' ID:'{self.sdk.branch_id}'"
        )
        return self.sdk.branch_id

    def get_branches(self) -> dict[str, str]:
        """Get a list of all branches in the project.

        Returns:
            dict[str, str]: A dictionary mapping branch names to branch IDs
        """
        branches = {"main": "main"}
        logger.info(f"Fetching branches for project {self.account_id}/{self.project_id}")
        for branch in self.sdk.fetch_branches().get("branches"):
            branches[branch.get("name")] = branch.get("branchId")
        logger.info(f"Fetched {len(branches)} branches branches={branches!r}")
        return branches

    def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch in the project.

        Args:
            branch_id (str): The ID of the branch to delete

        Returns:
            bool: True if the branch was deleted successfully.

        Raises:
            SourcererAPIError: If the API request fails.
        """
        if branch_id == "main":
            logger.error("Cannot delete 'main' branch.")
            return False

        logger.info(f"Deleting branch ID:'{branch_id}'")

        try:
            self.sdk.delete_branch(branch_id=branch_id)
        except SourcererAPIError as e:
            logger.debug(f"Failed to delete branch ID:'{branch_id}': {e}")
            raise

        logger.info(f"Successfully deleted branch ID:'{branch_id}'")
        return True

    def merge_branch(
        self, message: str, conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the current branch into main.

        Args:
            message (str): The merge commit message
            conflict_resolutions (list[dict[str, Any]]): A list of conflict resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            success (bool): True if the merge was successful, False otherwise
            list[dict[str, str]]: A list of conflict information if the merge failed, empty list if successful
            list[dict[str, str]]: A list of error information if the merge failed, empty list if successful
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == "main":
            logger.error("Cannot merge 'main' branch into itself.")
            return False, [], []

        logger.info(f"Merging branch '{self.sdk.branch_id}' into 'main'")

        try:
            result = self.sdk.merge_branch(
                expected_branch_last_known_sequence=self.sdk._last_known_sequence,
                deployment_message=message,
                conflict_resolutions=conflict_resolutions,
            )
        except SourcererAPIError as e:
            logger.error(f"Failed to merge branch '{self.sdk.branch_id}' into 'main': {e}")
            return False, [], []

        if result.get("hasConflicts", False) or result.get("errors", []):
            logger.error(
                f"Failed to merge branch '{self.sdk.branch_id}' into 'main' due to {len(result.get('conflicts', []))} conflicts and {len(result.get('errors', []))} errors"
            )
            conflicts = result.get("conflicts", [])
            errors = result.get("errors", [])
            return False, conflicts, errors

        logger.info(f"Successfully merged branch '{self.sdk.branch_id}' into 'main'")
        return True, [], []

    def get_branch_chat_info(self, branch_id: str) -> dict[str, Any]:
        """Get deployment info needed to start a draft chat on a branch."""
        self.assert_branch_exists()
        return self.sdk.get_branch_chat_info(branch_id)
