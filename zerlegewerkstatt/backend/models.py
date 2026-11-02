"""Eingaben und feste Zustände der Zerlege-Werkstatt."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Purpose = Literal["interoperability", "security_audit", "debugging", "preservation", "other_authorized"]
AnalysisType = Literal[
    "inspect-artifact",
    "inspect-android-package",
    "inspect-managed-artifact",
    "analyze-ghidra",
]


class CaseIn(BaseModel):
    project_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    title: str = Field(min_length=3, max_length=160)
    target: str = Field(default="", max_length=300)
    question: str = Field(min_length=10, max_length=2000)
    purpose: Purpose
    authorized: bool
    authorization_note: str = Field(default="", max_length=1000)


class AnalyzeIn(BaseModel):
    """Analyseanfrage. Nur Artefakt und Analysetyp, keine Pfade und Befehle."""

    artifact_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    analysis_type: AnalysisType
