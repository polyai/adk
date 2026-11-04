"""Building blocks of ``poly setup`` that are not commands: caller detection and telemetry.

Kept separate from ``cli_commands`` so the setup steps can be reshaped without
touching them, and so nothing here prints, prompts or exits.

Copyright PolyAI Limited
"""
