import logging
import requests
import hashlib
import os
import re
import json
import ipaddress
import uuid
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Basic Setup & Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# --- App Initialization & Documentation ---
app = FastAPI(
    title="Meta CAPI Event Connector",
    description="A secure and easy-to-use proxy to send server-side events to the Meta Conversions API (CAPI). This service handles PII hashing, server-data extraction, and payload formatting.",
    version="1.0.0",
    docs_url="/",  # Show docs at root for demo
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Router for Versioning ---
router_v1 = APIRouter(prefix="/v1")

# --- Pydantic Models ---
class ClientPayload(BaseModel):
    event_name: str
    event_time: int
    event_source_url: Optional[str] = None
    action_source: str
    user_data: dict  # Contains email, first_name, user_agent, etc.
    custom_data: Optional[dict] = None
    test_event_code: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "event_name": "Purchase",
                "event_time": 1703980800,
                "event_source_url": "https://example.com/checkout",
                "action_source": "website",
                "user_data": {
                    "email": "customer@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+1234567890",
                    "user_agent": "Mozilla/5.0...",
                    "fbc": "fb.1.1554763741205.AbCdEfGhIjKlMnOpQrStUvWxYz1234567890",
                    "fbp": "fb.1.1554763741205.1234567890"
                },
                "custom_data": {
                    "currency": "USD",
                    "value": 99.99,
                    "content_ids": ["product_123"],
                    "content_type": "product"
                }
            }
        }

# --- Helper Functions ---
FBP_REGEX = re.compile(r'^fb\.1\.\d+\.\d+$')

def hash_data(value: str) -> str:
    """
    Securely hash PII using SHA-256.
    Meta requires all PII to be hashed before transmission.
    """
    if not value:
        return ""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()

def extract_client_info(request: Request, payload: ClientPayload) -> dict:
    """
    Extract client IP and User Agent from request headers.
    These server-side signals improve Meta's event matching quality.
    """
    # Extract real client IP (handling proxy headers)
    x_forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.client.host
    
    # Prioritize User Agent from payload (original browser), fallback to request headers
    client_user_agent = payload.user_data.get("user_agent") or request.headers.get("user-agent", "")
    
    return {
        "ip": client_ip,
        "user_agent": client_user_agent
    }

def validate_and_clean_data(payload: ClientPayload, client_info: dict, request_id: str) -> dict:
    """
    Validate and clean all incoming data before sending to Meta.
    Ensures data integrity and prevents API errors.
    """
    # Validate IP address
    client_ip = client_info["ip"]
    try:
        if client_ip:
            ipaddress.ip_address(client_ip)
    except ValueError:
        logger.warning(f"[{request_id}] Invalid IP address: {client_ip}. Removing from payload.")
        client_ip = ""

    # Validate Facebook Pixel browser ID format
    fbp_val = payload.user_data.get("fbp", "")
    if fbp_val and not FBP_REGEX.match(fbp_val):
        logger.warning(f"[{request_id}] Invalid _fbp format: {fbp_val}. Removing from payload.")
        fbp_val = ""

    # Clean and validate custom_data
    custom_data = payload.custom_data or {}
    cleaned_custom_data = {
        k: v for k, v in custom_data.items() 
        if v is not None and str(v).lower() != 'null'
    }
    
    # Validate currency + value relationship
    if 'value' in cleaned_custom_data:
        try:
            cleaned_custom_data['value'] = float(cleaned_custom_data['value'])
        except (ValueError, TypeError):
            logger.warning(f"[{request_id}] Invalid 'value' in custom_data. Setting to 0.0.")
            cleaned_custom_data['value'] = 0.0
            
        if not cleaned_custom_data.get('currency'):
            raise HTTPException(
                status_code=422,
                detail={
                    "request_id": request_id,
                    "message": "Currency is required when value is provided."
                }
            )

    return {
        "client_ip": client_ip,
        "client_user_agent": client_info["user_agent"],
        "fbp": fbp_val,
        "fbc": payload.user_data.get("fbc", ""),
        "custom_data": cleaned_custom_data
    }

def hash_user_data(user_data: dict, request_id: str) -> dict:
    """
    Hash all PII according to Meta's requirements.
    Returns only non-empty hashed values.
    """
    pii_fields = {
        "em": user_data.get("email", ""),
        "fn": user_data.get("first_name", ""),
        "ln": user_data.get("last_name", ""),
        "ph": user_data.get("phone", ""),
        "country": user_data.get("country", ""),
        "ct": user_data.get("city", ""),
        "zp": user_data.get("zip", ""),
        "external_id": user_data.get("external_id", "")
    }
    
    # Hash and filter out empty values
    hashed_pii = {k: hash_data(v) for k, v in pii_fields.items() if v}
    
    # Log summary (for debugging/monitoring)
    pii_summary = ", ".join([f"{k}:present" for k in hashed_pii.keys()])
    logger.info(f"[{request_id}] PII processed: {pii_summary}")
    
    return hashed_pii

def build_meta_payload(payload: ClientPayload, validated_data: dict, hashed_pii: dict) -> dict:
    """
    Build the final payload in Meta's required format.
    """
    # Construct user_data object
    user_data = {
        "client_ip_address": validated_data["client_ip"] or None,
        "client_user_agent": validated_data["client_user_agent"] or None,
        "fbc": validated_data["fbc"] or None,
        "fbp": validated_data["fbp"] or None,
    }
    
    # Add hashed PII
    user_data.update(hashed_pii)
    
    # Remove None values for cleaner payload
    user_data = {k: v for k, v in user_data.items() if v is not None}
    
    # Build event data
    event_data = {
        "event_name": payload.event_name,
        "event_time": payload.event_time,
        "action_source": payload.action_source,
        "user_data": user_data,
        "custom_data": validated_data["custom_data"]
    }
    
    if payload.event_source_url:
        event_data["event_source_url"] = payload.event_source_url
    
    # Final Meta payload
    meta_payload = {"data": [event_data]}
    
    if payload.test_event_code:
        meta_payload["test_event_code"] = payload.test_event_code
        
    return meta_payload

# --- API Endpoints ---
@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "Meta CAPI Event Connector"}

@router_v1.post("/process-event", tags=["Events"])
def process_event(
    payload: ClientPayload,
    request: Request,
    x_meta_pixel_id: str = Header(..., description="Your Meta Pixel ID"),
    x_meta_access_token: str = Header(..., description="Your Meta CAPI Access Token")
):
    """
    Process and forward a server-side event to Meta's Conversions API.
    
    This endpoint:
    1. Extracts server-side signals (IP, User Agent)
    2. Validates and cleans all data
    3. Securely hashes PII
    4. Formats payload for Meta CAPI
    5. Forwards to Meta and returns response
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Processing {payload.event_name} event for Pixel {x_meta_pixel_id}")
    
    try:
        # Step 1: Extract client information
        client_info = extract_client_info(request, payload)
        
        # Step 2: Validate and clean data
        validated_data = validate_and_clean_data(payload, client_info, request_id)
        
        # Step 3: Hash PII
        hashed_pii = hash_user_data(payload.user_data, request_id)
        
        # Step 4: Build Meta payload
        meta_payload = build_meta_payload(payload, validated_data, hashed_pii)
        
        # Step 5: Send to Meta CAPI
        capi_url = f"https://graph.facebook.com/v19.0/{x_meta_pixel_id}/events?access_token={x_meta_access_token}"
        
        response = requests.post(capi_url, json=meta_payload, timeout=10)
        response.raise_for_status()
        
        logger.info(f"[{request_id}] Successfully sent event to Meta CAPI")
        
        return {
            "request_id": request_id,
            "status": "success",
            "message": "Event processed and sent to Meta CAPI successfully",
            "meta_response": response.json()
        }
        
    except requests.exceptions.RequestException as e:
        error_detail = f"Meta CAPI request failed: {str(e)}"
        if hasattr(e, 'response') and e.response:
            error_detail += f" | Response: {e.response.text}"
            
        logger.error(f"[{request_id}] {error_detail}")
        
        raise HTTPException(
            status_code=502,
            detail={
                "request_id": request_id,
                "message": "Failed to send event to Meta CAPI",
                "error": str(e)
            }
        )

# Include the versioned router
app.include_router(router_v1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)