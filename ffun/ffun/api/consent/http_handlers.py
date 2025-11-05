"""HTTP handlers for the consent API."""

from typing import Any

import fastapi
from fastapi import status
from fastapi.responses import RedirectResponse

from ffun.auth.dependencies import User
from ffun.auth.settings import settings as auth_settings
from ffun.core import logging
from ffun.domain import http as domain_http

logger = logging.get_module_logger()

router = fastapi.APIRouter(prefix="/spa/auth/consent", tags=["consent"])


def add_routes_to_app(app: fastapi.FastAPI) -> None:
    """Attach consent routes to the provided FastAPI application."""

    app.include_router(router)


def _get_hydra_admin_url() -> str:
    idp = auth_settings.get_idp_by_external_id(auth_settings.primary_oidc_service)

    if idp is None:
        logger.error("hydra_admin_not_configured")
        raise fastapi.HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Primary identity provider is not configured",
        )

    hydra_admin = (idp.extras or {}).get("hydra_admin")

    if not hydra_admin:
        logger.error("hydra_admin_url_missing")
        raise fastapi.HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hydra admin endpoint is not configured",
        )

    return hydra_admin.rstrip("/")


async def _hydra_get_consent_request(consent_challenge: str) -> dict[str, Any]:
    hydra_admin = _get_hydra_admin_url()
    url = f"{hydra_admin}/oauth2/auth/requests/consent"

    async with domain_http.client() as client:
        response = await client.get(url, params={"consent_challenge": consent_challenge})

    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "hydra_consent_fetch_failed",
            status=response.status_code,
            body=response.text,
        )
        raise fastapi.HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hydra consent lookup failed",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("hydra_consent_fetch_invalid_json", error=str(exc))
        raise fastapi.HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hydra consent lookup returned invalid payload",
        ) from exc

    return payload


async def _hydra_accept_consent(consent_challenge: str, consent_request: dict[str, Any]) -> str:
    hydra_admin = _get_hydra_admin_url()
    url = f"{hydra_admin}/oauth2/auth/requests/consent/{consent_challenge}/accept"

    payload = {
        "grant_scope": consent_request.get("requested_scope") or [],
        "grant_access_token_audience": consent_request.get("requested_access_token_audience") or [],
        "remember": False,
        "remember_for": 0,
    }

    async with domain_http.client() as client:
        response = await client.put(url, json=payload)

    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "hydra_consent_accept_failed",
            status=response.status_code,
            body=response.text,
        )
        raise fastapi.HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hydra consent acceptance failed",
        )

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("hydra_consent_accept_invalid_json", error=str(exc))
        raise fastapi.HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hydra consent acceptance returned invalid payload",
        ) from exc

    redirect_to = data.get("redirect_to")

    if not isinstance(redirect_to, str) or not redirect_to:
        logger.error("hydra_consent_accept_missing_redirect", payload=data)
        raise fastapi.HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hydra consent acceptance response missing redirect",
        )

    return redirect_to


@router.get("")
async def api_consent_accept(consent_challenge: str, user: User) -> RedirectResponse:
    """Automatically accept Hydra consent challenges and redirect the browser back to Hydra."""

    _ = user  # ensure dependency is evaluated

    consent_request = await _hydra_get_consent_request(consent_challenge)
    redirect_to = await _hydra_accept_consent(consent_challenge, consent_request)

    return RedirectResponse(url=redirect_to)
