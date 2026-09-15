"""Öffentliche Typen des HydraHive-Telefonie-Gatewayvertrags."""
from .fake import FakeTelephonyGateway
from .models import (
    CallDirection,
    CallRef,
    ConnectionProbe,
    ConnectionRef,
    ConnectionSpec,
    DialRequest,
    EventKind,
    GatewayEvent,
    GatewayHealth,
    SpeakRequest,
    TransportKind,
)
from .protocol import GatewayError, TelephonyGateway

__all__ = [
    "CallDirection",
    "CallRef",
    "ConnectionProbe",
    "ConnectionRef",
    "ConnectionSpec",
    "DialRequest",
    "EventKind",
    "FakeTelephonyGateway",
    "GatewayError",
    "GatewayEvent",
    "GatewayHealth",
    "SpeakRequest",
    "TelephonyGateway",
    "TransportKind",
]
