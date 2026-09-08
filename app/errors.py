class GatewayError(Exception):
    """Base gateway error."""


class ProviderNotConfiguredError(GatewayError):
    """Raised when a provider does not have required credentials."""


class ProviderRequestError(GatewayError):
    """Raised when an upstream provider request fails."""
