"""
Satellite Index Data proxy — on-demand passthrough to Agriverse API.
These endpoints are NOT synced to the local DB. They proxy requests
to the Agriverse API in real-time because tiff/index data is too large
to store locally.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx

from config import get_settings
from dependencies import authorize, get_current_user
from enums import UserRole
from models.user import User
from redis_client import redis_client

router = APIRouter(tags=["Satellite Data"])

settings = get_settings()
_TOKEN_KEY = "fams:sync:agriverse_token"


def _get_agriverse_token() -> str | None:
    """Retrieve the cached Agriverse API token (set by sync service)."""
    return redis_client.get(_TOKEN_KEY)


def _proxy_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.AGRIVERSE_API_URL,
        verify=settings.AGRIVERSE_VERIFY_SSL,
        timeout=30.0,
    )


def _proxy_headers(token: str | None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ── Proxy Endpoints ──────────────────────────────────────────


@router.get("/farm/{farm_id}/fields")
def get_farm_fields(
    farm_id: int,
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST,
        UserRole.FIELD_AGENT, UserRole.AGRONOMIST,
    )),
):
    """Proxy: farm fields with index time series (NDVI/MSAVI/EVI/NDRE)."""
    token = _get_agriverse_token()
    with _proxy_client() as client:
        try:
            r = client.get(f"/farm/{farm_id}/fields", headers=_proxy_headers(token))
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agriverse API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Agriverse API: {str(e)}")


class FieldCropRequest(BaseModel):
    fieldCropId: int

@router.post("/fieldcrop/get")
def get_field_crop_detail(
    body: FieldCropRequest,
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST,
        UserRole.FIELD_AGENT, UserRole.AGRONOMIST,
    )),
):
    """Proxy: full field crop detail with index time series + application history."""
    token = _get_agriverse_token()
    with _proxy_client() as client:
        try:
            r = client.post("/fieldcrop/get", json={"fieldcropId": body.fieldCropId}, headers=_proxy_headers(token))
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agriverse API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Agriverse API: {str(e)}")


class IndicesRequest(BaseModel):
    fieldCropId: int
    indexType: str

@router.post("/geotiff/fieldcrop/indices")
def get_fieldcrop_indices(body: IndicesRequest):
    """Proxy (public): index values + tile URLs for a field crop. No auth required."""
    with _proxy_client() as client:
        try:
            r = client.post("/geotiff/fieldcrop/indices", json={
                "fieldCropId": body.fieldCropId,
                "indexType": body.indexType,
            })
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agriverse API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Agriverse API: {str(e)}")


@router.get("/crop-stage-reference/{crop}")
def get_crop_stage_reference(crop: str):
    """Proxy (public): benchmark index ranges per growth stage."""
    with _proxy_client() as client:
        try:
            r = client.get(f"/crop-stage-reference/{crop}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agriverse API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Agriverse API: {str(e)}")


@router.get("/farm/by-district-id/{district_id}")
def get_farms_by_district(
    district_id: int,
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST,
        UserRole.FIELD_AGENT, UserRole.AGRONOMIST,
    )),
):
    """Proxy: district-wide farm listing with full index set."""
    token = _get_agriverse_token()
    with _proxy_client() as client:
        try:
            r = client.get(f"/farm/by-district-id/{district_id}", headers=_proxy_headers(token))
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agriverse API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Agriverse API: {str(e)}")
