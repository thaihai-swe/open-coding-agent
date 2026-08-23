"""Phase-precondition primitives for the embedded workflow harness."""
import os
from pathlib import Path

from core._lib.artifacts import resolve_artifact_path


class Phase:
    def __init__(self, name, preconditions=None, **_ignored):
        self.name = name
        self.preconditions = preconditions or []

    def check_preconditions(self, feature_dir, feature_slug=None):
        failures = []
        slug = feature_slug or Path(feature_dir).name
        for precondition in self.preconditions:
            artifact = resolve_artifact_path(feature_dir, precondition["artifact"], slug)
            check = precondition.get("check", "exists")
            if check == "exists" and not os.path.exists(artifact):
                failures.append(f"Required artifact missing: {artifact}")
            elif check == "contains_stale" and os.path.exists(artifact):
                with open(artifact, encoding="utf-8", errors="replace") as handle:
                    if "[:HALT" in handle.read():
                        failures.append(f"Artifact has [:HALT marker: {artifact}")
        return failures


class Lifecycle:
    """Expose canonical phases with optional adopter overrides, without generated state."""
    def __init__(self, config):
        self.lifecycle = getattr(config, "lifecycle", None)
        if self.lifecycle is None and isinstance(config, dict):
            self.lifecycle = config
        self.phases = [Phase(**phase) for phase in self.lifecycle.get("phases", [])]
        self.states = list(self.lifecycle.get("states", []))
        self.phase_mapping = dict(self.lifecycle.get("phase_mapping", {}))
        self.transitions = list(self.lifecycle.get("transitions", []))

    def states_for_phase(self, phase_name):
        return [
            state for state, phase in self.phase_mapping.items()
            if phase == phase_name
        ]

    def check_transition(self, current_state, target_phase):
        """Check whether a feature may enter the requested phase.

        A state already mapped to the target phase is stable. Otherwise the
        target phase is reachable when one declared transition leads to a
        state mapped to it.
        """
        if not current_state or current_state not in self.phase_mapping:
            return True, []
        if self.phase_mapping[current_state] == target_phase:
            return True, []
        targets = set(self.states_for_phase(target_phase))
        reachable = {
            transition.get("to")
            for transition in self.transitions
            if transition.get("from") == current_state
        }
        if reachable & targets:
            return True, []
        return False, [
            f"illegal lifecycle transition: {current_state} -> {target_phase}"
        ]

    def check_state_transition(self, current_state, target_state):
        """Check a status.md token transition against declared states."""
        if target_state not in self.states:
            return False, [f"unknown lifecycle state: {target_state}"]
        if not current_state or current_state not in self.states:
            return True, []
        if current_state == target_state:
            return True, []
        allowed = {
            transition.get("to")
            for transition in self.transitions
            if transition.get("from") == current_state
        }
        if target_state in allowed:
            return True, []
        return False, [
            f"illegal lifecycle transition: {current_state} -> {target_state}"
        ]
