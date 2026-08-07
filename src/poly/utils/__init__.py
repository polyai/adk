"""Utility functions for Agent Development Kit.

Utilities live in focused submodules — ``poly.utils.credentials``,
``poly.utils.merge``, ``poly.utils.stub_gen``, ``poly.utils.decorators``,
``poly.utils.variable_references`` and ``poly.utils.commands`` — with the
public names re-exported here for convenience and backwards compatibility.

Copyright PolyAI Limited
"""

from poly.utils.commands import create_command_webchat_channel_update_status
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    any_credentials_exist,
    retrieve_api_key,
    save_api_key_credential_file,
)
from poly.utils.decorators import (
    export_decorators,
    func_description,
    func_latency_control,
    func_parameter,
)
from poly.utils.json_io import diff_dicts, read_json_file, write_json_file
from poly.utils.merge import merge_rtc_dicts, merge_strings
from poly.utils.stub_gen import create_import_file_contents, save_imports
from poly.utils.variable_references import (
    FUNCTION_TYPE_TO_VAR_REF_FIELD,
    compute_variable_references,
)

__all__ = [
    "CREDENTIALS_FILE_PATH",
    "FUNCTION_TYPE_TO_VAR_REF_FIELD",
    "any_credentials_exist",
    "compute_variable_references",
    "diff_dicts",
    "create_command_webchat_channel_update_status",
    "create_import_file_contents",
    "export_decorators",
    "func_description",
    "func_latency_control",
    "func_parameter",
    "merge_rtc_dicts",
    "merge_strings",
    "read_json_file",
    "retrieve_api_key",
    "save_api_key_credential_file",
    "save_imports",
    "write_json_file",
]
