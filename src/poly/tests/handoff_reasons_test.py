"""Handoff reasons, the transfer message and Transfer test calls in config/handoffs.yaml.

Drives the project offline from a projection: render the projection to files, then
dry-run push the files back against it.
"""

import copy
import os
import tempfile

import pytest
import yaml

from poly.handlers.protobuf.handoff_pb2 import HANDOFF_CHANNEL_CALL
from poly.project import AgentStudioProject
from poly.resources import HandoffReason, HandoffTransferMessage
from poly.resources.handoff import ReasonOutcome
from poly.resources.resource import MultiResourceYamlResource
from poly.resources.resource_utils import dump_yaml

HANDOFFS = os.path.join("config", "handoffs.yaml")


def destination(name, *, is_default=False, skip_test_calls=None):
    state = {
        "id": name,
        "name": name,
        "description": f"{name} team",
        "active": True,
        "isDefault": is_default,
        "sipConfig": {"config": {"$case": "refer", "value": {"phoneNumber": "+441234567890"}}},
        "sipHeaders": {"headers": []},
    }
    if skip_test_calls is not None:
        state["skipTestCallTransfers"] = skip_test_calls
    return state


def outcome(case, value=None):
    return {"outcome": {"$case": case, "value": value or {}}}


def projection_with_reasons():
    return {
        "handoff": {
            "handoffs": {
                "ids": ["HANDOFF-1", "HANDOFF-2"],
                "entities": {
                    "HANDOFF-1": destination("Front desk", is_default=True),
                    "HANDOFF-2": destination("Billing", skip_test_calls=True),
                },
            },
            "reasons": {
                "ids": ["REASON-1", "REASON-2", "REASON-3"],
                "entities": {
                    "REASON-1": {
                        "id": "REASON-1",
                        "key": "BILLING",
                        "name": "Billing dispute",
                        "description": "The caller disputes a charge.",
                        "active": True,
                        "outcomes": {
                            "call": outcome(
                                "transfer", {"destinationId": "HANDOFF-2", "wording": "One moment."}
                            ),
                            "chat": outcome(
                                "message", {"message": "Point them to the billing page."}
                            ),
                        },
                    },
                    "REASON-2": {
                        "id": "REASON-2",
                        "key": "SPEAK_TO",
                        "name": "Speak to a person",
                        "description": "The caller asks for a person.",
                        "active": True,
                        "outcomes": {
                            "call": outcome("transfer", {"destinationId": "HANDOFF-1"}),
                            "chat": outcome("notOffered"),
                        },
                    },
                    "REASON-3": {
                        "id": "REASON-3",
                        "key": "OPENING_HOURS",
                        "name": "Opening hours",
                        "description": "The caller asks when you are open.",
                        "active": True,
                        "outcomes": {"call": outcome("message", {"message": "9 to 5."})},
                    },
                },
            },
            "settings": {"callTransferMessage": "Let me put you through."},
        }
    }


def write_config(directory):
    config = {"region": "dev", "account_id": "dummy", "project_id": "dummy", "branch_id": "main"}
    with open(os.path.join(directory, "project.yaml"), "w", encoding="utf-8") as f:
        f.write(dump_yaml(config))


def collect(directory):
    files = {}
    for root, _, names in os.walk(directory):
        for name in names:
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as f:
                files[os.path.relpath(path, directory)] = f.read()
    return files


def render(projection):
    with tempfile.TemporaryDirectory() as tmp:
        write_config(tmp)
        project = AgentStudioProject.from_file_path(tmp)
        project.pull_project(projection_json=projection, force=True)
        MultiResourceYamlResource._file_cache.clear()
        return collect(tmp)


def push(files, projection):
    """Dry-run push files against projection; returns (success, message, commands)."""
    with tempfile.TemporaryDirectory() as tmp:
        for rel, content in files.items():
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
            with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                f.write(content)
        write_config(tmp)
        project = AgentStudioProject.from_file_path(tmp)
        conflicts, _ = project.pull_project(projection_json=projection, force=False)
        assert not conflicts
        try:
            return project.push_project(projection_json=projection, dry_run=True)
        finally:
            MultiResourceYamlResource._file_cache.clear()


def edit_handoffs(files, change):
    data = yaml.safe_load(files[HANDOFFS])
    change(data)
    return {**files, HANDOFFS: yaml.dump(data, sort_keys=False)}


def test_pulled_file():
    data = yaml.safe_load(render(projection_with_reasons())[HANDOFFS])
    assert list(data) == ["handoffs", "reasons", "transfer_message"]
    front_desk, billing = data["handoffs"]
    assert "transfer_test_calls" not in front_desk
    assert billing["transfer_test_calls"] is False
    assert data["reasons"][0] == {
        "name": "Billing dispute",
        "key": "BILLING",
        "description": "The caller disputes a charge.",
        "call": {"transfer_to": "Billing", "wording": "One moment."},
        "chat": {"message": "Point them to the billing page."},
    }
    assert data["reasons"][1]["call"] == {"transfer_to": "Front desk"}
    assert data["reasons"][1]["chat"] == "not_offered"
    assert data["reasons"][2]["call"] == {"message": "9 to 5."}
    assert "chat" not in data["reasons"][2]
    assert data["transfer_message"] == {"call": "Let me put you through."}


def test_pull_then_push_changes_nothing():
    projection = projection_with_reasons()
    files = render(projection)
    _, _, commands = push(files, projection)
    assert [c.type for c in commands] == []


def test_transfer_test_calls_round_trips():
    projection = projection_with_reasons()

    def flip(data):
        data["handoffs"][0]["transfer_test_calls"] = False
        del data["handoffs"][1]["transfer_test_calls"]

    _, _, commands = push(edit_handoffs(render(projection), flip), projection)
    updates = {
        c.handoff_update.id: c.handoff_update for c in commands if c.type == "handoff_update"
    }
    assert updates["HANDOFF-1"].skip_test_call_transfers is True
    assert updates["HANDOFF-2"].skip_test_call_transfers is False


def test_existing_config_without_reasons_support_is_unchanged():
    projection = projection_with_reasons()
    del projection["handoff"]["reasons"]
    del projection["handoff"]["settings"]
    projection["handoff"]["handoffs"]["entities"]["HANDOFF-2"].pop("skipTestCallTransfers")
    data = yaml.safe_load(render(projection)[HANDOFFS])
    assert list(data) == ["handoffs"]
    assert all("transfer_test_calls" not in h for h in data["handoffs"])


def test_reasons_key_is_written_with_no_reasons():
    projection = projection_with_reasons()
    projection["handoff"]["reasons"] = {"ids": [], "entities": {}}
    del projection["handoff"]["settings"]
    files = render(projection)
    assert yaml.safe_load(files[HANDOFFS])["reasons"] == []
    _, _, commands = push(files, projection)
    assert [c.type for c in commands] == []


def test_file_without_reasons_key_keeps_the_projects_reasons():
    projection = projection_with_reasons()

    def drop(data):
        del data["reasons"]
        del data["transfer_message"]

    _, _, commands = push(edit_handoffs(render(projection), drop), projection)
    assert [c.type for c in commands] == []


def test_new_reason_and_destination_in_one_push():
    projection = projection_with_reasons()

    def add(data):
        data["handoffs"].append(
            {
                "name": "Sales",
                "description": "Sales team",
                "is_default": False,
                "sip_config": {"method": "bye"},
            }
        )
        data["reasons"].append(
            {
                "name": "Buy something",
                "description": "The caller wants to buy.",
                "call": {"transfer_to": "Sales"},
                "chat": "not_offered",
            }
        )

    _, _, commands = push(edit_handoffs(render(projection), add), projection)
    types = [c.type for c in commands]
    assert types == ["handoff_create", "handoff_reason_create"]
    sales = commands[0].handoff_create
    create = commands[1].handoff_reason_create
    assert create.outcomes.call.transfer.destination_id == sales.id
    assert create.outcomes.chat.HasField("not_offered")
    assert not create.HasField("key")


def test_edited_reason_and_message_are_updated():
    projection = projection_with_reasons()

    def edit(data):
        data["reasons"][0]["description"] = "The caller disputes a charge on their bill."
        data["reasons"][0]["call"] = {"transfer_to": "Front desk"}
        data["transfer_message"]["call"] = ""

    _, _, commands = push(edit_handoffs(render(projection), edit), projection)
    by_type = {c.type: c for c in commands}
    assert set(by_type) == {"handoff_reason_update", "handoff_settings_set_transfer_message"}
    update = by_type["handoff_reason_update"].handoff_reason_update
    assert update.id == "REASON-1"
    assert update.description == "The caller disputes a charge on their bill."
    assert update.outcomes.call.transfer.destination_id == "HANDOFF-1"
    assert not update.outcomes.call.transfer.HasField("wording")
    message = by_type["handoff_settings_set_transfer_message"].handoff_settings_set_transfer_message
    assert message.channel == HANDOFF_CHANNEL_CALL
    assert message.HasField("message") and message.message == ""


def test_reasons_are_deleted_before_their_destination():
    projection = projection_with_reasons()

    def remove(data):
        del data["handoffs"][1]
        data["reasons"] = [r for r in data["reasons"] if r["name"] != "Billing dispute"]

    _, _, commands = push(edit_handoffs(render(projection), remove), projection)
    assert [c.type for c in commands] == ["handoff_reason_delete", "handoff_delete"]
    assert commands[0].handoff_reason_delete.id == "REASON-1"
    assert commands[1].handoff_delete.id == "HANDOFF-2"


def test_empty_reasons_list_deletes_them_all():
    projection = projection_with_reasons()
    files = edit_handoffs(render(projection), lambda d: d.update(reasons=[]))
    _, _, commands = push(files, projection)
    assert sorted(c.handoff_reason_delete.id for c in commands) == [
        "REASON-1",
        "REASON-2",
        "REASON-3",
    ]


def test_renamed_reason_keeps_its_id_by_key():
    projection = projection_with_reasons()
    files = edit_handoffs(
        render(projection), lambda d: d["reasons"][1].update(name="Talk to a human")
    )
    _, _, commands = push(files, projection)
    assert [c.type for c in commands] == ["handoff_reason_update"]
    assert commands[0].handoff_reason_update.id == "REASON-2"
    assert commands[0].handoff_reason_update.name == "Talk to a human"


@pytest.mark.parametrize(
    "value, error",
    [
        ({"transfer_to": "X", "message": "Y"}, "can't go with"),
        ({"kind": "transfer"}, "unknown keys"),
        ("transfer", "must be `not_offered`"),
        ({"wording": "Hi"}, "needs `transfer_to` or `message`"),
    ],
)
def test_outcome_shape_is_strict(value, error):
    with pytest.raises(ValueError, match=error):
        ReasonOutcome.from_yaml_value(value, "call", "R")


def test_reason_rules():
    def reason(**changes):
        fields = {
            "resource_id": "R",
            "name": "Complaint",
            "description": "The caller complains.",
            "call": ReasonOutcome(kind="message", message="Apologise."),
        }
        return HandoffReason(**{**fields, **changes})

    reason().validate(resource_mappings=[])
    with pytest.raises(ValueError, match="key"):
        reason(key="lower").validate(resource_mappings=[])
    with pytest.raises(ValueError, match="needs a description"):
        reason(description=" ").validate(resource_mappings=[])
    with pytest.raises(ValueError, match="chat can't transfer"):
        reason(chat=ReasonOutcome(kind="transfer", destination_id="H")).validate(
            resource_mappings=[]
        )
    with pytest.raises(ValueError, match="not a destination"):
        reason(call=ReasonOutcome(kind="transfer", destination_id="Nowhere")).validate(
            resource_mappings=[]
        )
    with pytest.raises(ValueError, match="keys must be unique"):
        HandoffReason.validate_collection(
            {"A": reason(key="K"), "B": reason(resource_id="B", name="Other", key="K")}
        )


def test_transfer_message_is_call_only():
    message = HandoffTransferMessage.from_yaml_dict({"call": "Hi", "chat": "Hello"}, "id")
    with pytest.raises(ValueError, match="only takes `call`"):
        message.validate()
    unset = HandoffTransferMessage.from_yaml_dict({"call": None}, "id").build_update_proto()
    assert unset.channel == HANDOFF_CHANNEL_CALL
    assert not unset.HasField("message")
    silent = HandoffTransferMessage.from_yaml_dict({"call": ""}, "id").build_update_proto()
    assert silent.HasField("message") and silent.message == ""


def test_chat_transfer_message_is_not_pulled():
    projection = copy.deepcopy(projection_with_reasons())
    projection["handoff"]["settings"] = {"chatTransferMessage": "Hello"}
    assert "transfer_message" not in yaml.safe_load(render(projection)[HANDOFFS])
