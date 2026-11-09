import hmac
import ipaddress

from flask import current_app, request


def _trusted_networks():
    raw_value = current_app.config.get("INTERNAL_TRUSTED_SUBNETS", "")
    networks = []

    for item in raw_value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            continue

    return networks


def has_valid_internal_api_key():
    internal_api_key = current_app.config.get("INTERNAL_API_KEY", "")
    provided_api_key = request.headers.get("X-Internal-API-Key", "")

    if not internal_api_key or not provided_api_key:
        return False

    return hmac.compare_digest(provided_api_key, internal_api_key)


def is_trusted_internal_request():
    # HR authorization cannot be bypassed by a source IP, Docker subnet or proxy.
    # Existing MQTT/PHP integrations must send the configured shared key.
    return has_valid_internal_api_key()
