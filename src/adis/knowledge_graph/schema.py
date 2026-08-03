"""Knowledge graph node/edge schema for roads, buildings, hospitals, shelters."""
from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    INTERSECTION = "intersection"
    BUILDING = "building"
    HOSPITAL = "hospital"
    SHELTER = "shelter"


class RoadStatus(str, Enum):
    CLEAR = "clear"
    PARTIAL = "partially-blocked"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class FacilityStatus(str, Enum):
    FUNCTIONAL = "functional"
    DEGRADED = "degraded"
    NON_FUNCTIONAL = "non-functional"
    UNKNOWN = "unknown"
