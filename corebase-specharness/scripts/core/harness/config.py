from pathlib import Path

from core._lib.yaml_reader import load as load_yaml
from core.harness.exceptions import ConfigError
from core.harness.gates import Gate

_VALID_ON_FAIL = {"block", "warn", "continue"}
_VALID_VERIFICATION_MODES = {"advisory", "blocking"}


class HarnessConfig:
    """Adopter-owned verification configuration and lifecycle overrides."""

    def __init__(self, config_path):
        self.path = Path(config_path)
        if not self.path.is_file():
            raise ConfigError(f"Config not found: {config_path}")
        self.data = load_yaml(self.path) or {}
        if not isinstance(self.data, dict):
            raise ConfigError("harness-config.yaml must be a mapping")
        self.validate()
        self.lifecycle = self._load_lifecycle()

    def _load_lifecycle(self):
        path = self.path.with_name("state-machine.yaml")
        if not path.is_file():
            raise ConfigError(f"State machine not found: {path}")
        lifecycle = load_yaml(path) or {}
        overrides = self.data.get("lifecycle_overrides") or {}
        if not isinstance(overrides, dict):
            raise ConfigError("lifecycle_overrides must be a mapping")
        lifecycle = self._merge_lifecycle(lifecycle, overrides)
        self._validate_lifecycle(lifecycle)
        return lifecycle

    @staticmethod
    def _merge_named(items, overrides):
        values = {item["name"]: dict(item) for item in items}
        order = [item["name"] for item in items]
        for item in overrides:
            name = item.get("name") if isinstance(item, dict) else None
            current = values.get(name)
            if current and "preconditions" in item:
                merged = dict(current)
                merged.update(item)
                known = {
                    (check.get("artifact"), check.get("check"))
                    for check in current.get("preconditions", [])
                    if isinstance(check, dict)
                }
                merged["preconditions"] = list(current.get("preconditions", [])) + [
                    check for check in item["preconditions"]
                    if not isinstance(check, dict)
                    or (check.get("artifact"), check.get("check")) not in known
                ]
                values[name] = merged
                continue
            if name not in values:
                order.append(name)
            values[name] = dict(item)
        return [values[name] for name in order]

    def _merge_lifecycle(self, lifecycle, overrides):
        if not isinstance(lifecycle, dict):
            return lifecycle
        result = dict(lifecycle)
        if "phases" in overrides:
            if not isinstance(overrides["phases"], list):
                raise ConfigError("lifecycle_overrides.phases must be a list")
            result["phases"] = self._merge_named(result.get("phases", []), overrides["phases"])
        if "states" in overrides:
            if not isinstance(overrides["states"], list):
                raise ConfigError("lifecycle_overrides.states must be a list")
            result["states"] = list(dict.fromkeys((result.get("states", []) + overrides["states"])))
        if "phase_mapping" in overrides:
            if not isinstance(overrides["phase_mapping"], dict):
                raise ConfigError("lifecycle_overrides.phase_mapping must be a mapping")
            result["phase_mapping"] = {**result.get("phase_mapping", {}), **overrides["phase_mapping"]}
        if "transitions" in overrides:
            if not isinstance(overrides["transitions"], list):
                raise ConfigError("lifecycle_overrides.transitions must be a list")
            result["transitions"] = result.get("transitions", []) + overrides["transitions"]
        unknown = set(overrides) - {"phases", "states", "phase_mapping", "transitions"}
        if unknown:
            raise ConfigError(f"lifecycle_overrides has unknown fields: {', '.join(sorted(unknown))}")
        return result

    @staticmethod
    def _validate_lifecycle(lifecycle):
        if not isinstance(lifecycle, dict):
            raise ConfigError("state-machine.yaml must be a mapping")
        phases = lifecycle.get("phases")
        if not isinstance(phases, list) or not phases:
            raise ConfigError("state-machine.yaml must contain a phases list")
        names = set()
        for index, phase in enumerate(phases):
            if not isinstance(phase, dict) or not isinstance(phase.get("name"), str) or not phase["name"]:
                raise ConfigError(f"Phase at index {index} missing name")
            if phase["name"] in names:
                raise ConfigError(f"Duplicate phase name: {phase['name']}")
            names.add(phase["name"])
            preconditions = phase.get("preconditions", [])
            if not isinstance(preconditions, list):
                raise ConfigError(f"Phase {phase['name']} preconditions must be a list")
            for precondition in preconditions:
                if not isinstance(precondition, dict) or not precondition.get("artifact"):
                    raise ConfigError(f"Phase {phase['name']} has a precondition without artifact")
        states = lifecycle.get("states")
        if not isinstance(states, list) or not states or not all(isinstance(state, str) and state for state in states):
            raise ConfigError("state-machine.yaml states must be a non-empty string list")
        if len(states) != len(set(states)):
            raise ConfigError("state-machine.yaml states must be unique")
        phase_mapping = lifecycle.get("phase_mapping")
        if not isinstance(phase_mapping, dict) or set(phase_mapping) != set(states):
            raise ConfigError("state-machine.yaml phase_mapping must map every state")
        for state, phase in phase_mapping.items():
            if phase not in names:
                raise ConfigError(f"State {state} maps to unknown phase: {phase}")
        transitions = lifecycle.get("transitions")
        if not isinstance(transitions, list):
            raise ConfigError("state-machine.yaml transitions must be a list")
        for transition in transitions:
            if not isinstance(transition, dict) or set(transition) != {"from", "to"}:
                raise ConfigError("State transition must contain from and to")
            if transition["from"] not in phase_mapping or transition["to"] not in phase_mapping:
                raise ConfigError("State transition references an unknown state")

    def _default_on_fail(self):
        value = (self.data.get("gate_defaults") or {}).get("on_fail", "block")
        return value if value in _VALID_ON_FAIL else "block"

    def verification_mode(self):
        verification = self.data.get("verification") or {}
        value = verification.get("mode", "blocking")
        return value if value in _VALID_VERIFICATION_MODES else "blocking"

    def _make_gate(self, item):
        return Gate(
            name=item["name"], command=item["command"],
            on_fail=item.get("on_fail") or ("warn" if not item.get("required", True) else self._default_on_fail()),
            config=self.data, category=item.get("category", ""),
            required=item.get("required", True), timeout_seconds=item.get("timeout_seconds"),
            allow_shell=item.get("allow_shell", False),
            paths=item.get("paths") or [],
        )

    def validate(self):
        if not isinstance(self.data, dict):
            raise ConfigError("harness-config.yaml must be a mapping")
        if "phases" in self.data:
            raise ConfigError("harness-config.yaml must not contain phases; use lifecycle_overrides")
        for index, gate in enumerate(self.data.get("gates", [])):
            if not isinstance(gate, dict) or not gate.get("name"):
                raise ConfigError(f"Gate at index {index} missing name")
            command = gate.get("command")
            if not isinstance(command, (list, tuple)) or not command:
                if not gate.get("allow_shell", False) or not isinstance(command, str) or not command.strip():
                    raise ConfigError(f"Gate '{gate['name']}' command must be a non-empty argv list")
            if gate.get("allow_shell", False) and not str(gate.get("shell_rationale", "")).strip():
                raise ConfigError(f"Gate '{gate['name']}' allow_shell requires shell_rationale")
            if gate.get("on_fail", self._default_on_fail()) not in _VALID_ON_FAIL:
                raise ConfigError(f"Gate '{gate['name']}' has invalid on_fail")
            paths = gate.get("paths")
            if paths is not None:
                if not isinstance(paths, list) or not all(isinstance(item, str) and item.strip() for item in paths):
                    raise ConfigError(f"Gate '{gate['name']}' paths must be a list of non-empty strings")
        project_setup = self.data.get("project_setup") or {}
        if not isinstance(project_setup, dict):
            raise ConfigError("project_setup must be a mapping")
        if project_setup.get("status", "deferred") not in {"deferred", "in_progress", "ready"}:
            raise ConfigError("project_setup.status must be deferred, in_progress, or ready")
        verification = self.data.get("verification") or {}
        if not isinstance(verification, dict):
            raise ConfigError("verification must be a mapping")
        if verification.get("mode", "blocking") not in _VALID_VERIFICATION_MODES:
            raise ConfigError("verification.mode must be advisory or blocking")
        thresholds = self.data.get("thresholds") or {}
        for key, value in thresholds.items():
            if key.endswith(("_lines", "_seconds", "_budget", "_warn", "_hard", "_breach", "_tokens")):
                try:
                    if int(value) <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ConfigError(f"thresholds.{key} must be positive")

    def project_setup_status(self):
        return (self.data.get("project_setup") or {}).get("status", "deferred")

    def session_warn_tokens(self):
        return int((self.data.get("thresholds") or {}).get("session_warn_tokens") or 40000)

    def session_hard_tokens(self):
        return int((self.data.get("thresholds") or {}).get("session_hard_tokens") or 80000)

    def get_gates(self):
        return [self._make_gate(gate) for gate in self.data.get("gates", [])]
