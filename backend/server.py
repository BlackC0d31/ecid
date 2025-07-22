from fastapi import FastAPI, APIRouter, HTTPException, File, UploadFile, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime, timedelta
import hashlib
import base64
import json
import jwt
from enum import Enum
import aiofiles

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="CID Insurance Integration System", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Enums
class InsuranceProvider(str, Enum):
    ALLIANZ = "allianz"
    UNIPOLSAI = "unipolsai" 
    GENERALI = "generali"
    AXA = "axa"

class AuthMethod(str, Enum):
    JWT = "jwt"
    OAUTH2 = "oauth2"

class CIDStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"

# Models
class PersonInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    surname: str = Field(..., min_length=2, max_length=100)
    license_plate: str = Field(..., min_length=5, max_length=10)
    insurance_company: InsuranceProvider
    policy_number: str = Field(..., min_length=5, max_length=50)

class AccidentDetails(BaseModel):
    timestamp: datetime
    location: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=1000)
    circumstances: List[str] = Field(..., min_items=1)
    damage_description: str = Field(..., max_length=500)

class CIDData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    person_a: PersonInfo
    person_b: PersonInfo
    accident_details: AccidentDetails
    created_at: datetime = Field(default_factory=datetime.utcnow)
    signatures: Dict[str, str] = Field(default_factory=dict)  # person_id -> signature_data
    status: CIDStatus = CIDStatus.PENDING

class CIDSubmission(BaseModel):
    cid_data: Dict[str, Any]
    pdf_base64: Optional[str] = None
    pdf_hash: Optional[str] = None

class InsuranceAPIResponse(BaseModel):
    success: bool
    claim_id: Optional[str] = None
    message: str
    provider: InsuranceProvider
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Dict[str, Any] = Field(default_factory=dict)

class CIDRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cid_data: Dict[str, Any]
    pdf_hash: str
    pdf_base64: str
    claim_id: str
    status: CIDStatus
    api_responses: List[InsuranceAPIResponse] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Authentication Classes
class AuthenticationManager:
    def __init__(self):
        self.mock_tokens = {
            InsuranceProvider.ALLIANZ: "mock_allianz_token_12345",
            InsuranceProvider.UNIPOLSAI: "mock_unipolsai_token_67890", 
            InsuranceProvider.GENERALI: "mock_generali_token_abcde",
            InsuranceProvider.AXA: "mock_axa_token_fghij"
        }
    
    async def get_jwt_token(self, provider: InsuranceProvider) -> str:
        """Generate or retrieve JWT token for insurance provider"""
        payload = {
            "provider": provider.value,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "sub": "cid_system"
        }
        return jwt.encode(payload, "mock_secret_key", algorithm="HS256")
    
    async def get_oauth2_token(self, provider: InsuranceProvider) -> str:
        """Get OAuth2 token for insurance provider (mock implementation)"""
        return f"oauth2_{provider.value}_{int(datetime.utcnow().timestamp())}"
    
    async def authenticate(self, provider: InsuranceProvider, method: AuthMethod = AuthMethod.JWT) -> str:
        """Main authentication method"""
        if method == AuthMethod.JWT:
            return await self.get_jwt_token(provider)
        else:
            return await self.get_oauth2_token(provider)

# Insurance Provider Classes
class BaseInsuranceProvider:
    def __init__(self, provider: InsuranceProvider, auth_manager: AuthenticationManager):
        self.provider = provider
        self.auth_manager = auth_manager
        self.base_url = self._get_base_url()
    
    def _get_base_url(self) -> str:
        """Get base URL for insurance provider (mock endpoints)"""
        urls = {
            InsuranceProvider.ALLIANZ: "https://api-mock.allianz.com/v1",
            InsuranceProvider.UNIPOLSAI: "https://api-mock.unipolsai.it/v2", 
            InsuranceProvider.GENERALI: "https://api-mock.generali.com/claims",
            InsuranceProvider.AXA: "https://api-mock.axa.com/submit"
        }
        return urls[self.provider]
    
    async def submit_cid(self, cid_data: Dict[str, Any], pdf_base64: str, pdf_hash: str) -> InsuranceAPIResponse:
        """Submit CID to insurance provider - base implementation"""
        auth_token = await self.auth_manager.authenticate(self.provider)
        
        # Mock API call simulation
        await asyncio.sleep(0.5)  # Simulate API latency
        
        # Generate mock claim ID
        claim_id = f"{self.provider.value.upper()}-{str(uuid.uuid4())[:8]}"
        
        # Mock response based on provider
        mock_response = self._generate_mock_response(claim_id, cid_data)
        
        return InsuranceAPIResponse(
            success=True,
            claim_id=claim_id,
            message=f"CID successfully submitted to {self.provider.value}",
            provider=self.provider,
            raw_response=mock_response
        )
    
    def _generate_mock_response(self, claim_id: str, cid_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock API response"""
        return {
            "claimId": claim_id,
            "status": "received",
            "estimatedProcessingTime": "3-5 business days",
            "referenceNumber": f"REF-{claim_id}",
            "submissionTimestamp": datetime.utcnow().isoformat(),
            "acknowledgment": f"Claim received by {self.provider.value}"
        }

class AllianzProvider(BaseInsuranceProvider):
    async def submit_cid(self, cid_data: Dict[str, Any], pdf_base64: str, pdf_hash: str) -> InsuranceAPIResponse:
        """Allianz-specific implementation"""
        auth_token = await self.auth_manager.authenticate(self.provider)
        
        # Allianz-specific payload format
        payload = {
            "clientToken": auth_token,
            "documentType": "CID",
            "claimData": {
                "parties": [
                    {
                        "role": "party_a",
                        "personalInfo": cid_data.get("person_a", {}),
                    },
                    {
                        "role": "party_b", 
                        "personalInfo": cid_data.get("person_b", {}),
                    }
                ],
                "incident": cid_data.get("accident_details", {}),
                "documentHash": pdf_hash
            },
            "attachments": [
                {
                    "type": "signed_cid",
                    "format": "pdf",
                    "content": pdf_base64[:100] + "..."  # Truncated for demo
                }
            ]
        }
        
        # Mock successful response
        claim_id = f"ALZ-{str(uuid.uuid4())[:8]}"
        return InsuranceAPIResponse(
            success=True,
            claim_id=claim_id,
            message="CID successfully submitted to Allianz",
            provider=self.provider,
            raw_response={
                "allianzClaimId": claim_id,
                "status": "ACCEPTED",
                "processingReference": f"ALZ-REF-{int(datetime.utcnow().timestamp())}",
                "estimatedResolution": "72 hours"
            }
        )

class UnipolProvider(BaseInsuranceProvider):
    async def submit_cid(self, cid_data: Dict[str, Any], pdf_base64: str, pdf_hash: str) -> InsuranceAPIResponse:
        """UnipolSai-specific implementation"""
        auth_token = await self.auth_manager.authenticate(self.provider)
        
        # UnipolSai-specific format
        claim_id = f"UNI-{str(uuid.uuid4())[:8]}"
        return InsuranceAPIResponse(
            success=True,
            claim_id=claim_id,
            message="CID successfully submitted to UnipolSai",
            provider=self.provider,
            raw_response={
                "unipolClaimReference": claim_id,
                "submissionStatus": "RICEVUTO",
                "praticaNumero": f"PRT-{int(datetime.utcnow().timestamp())}",
                "tempoElaborazione": "2-4 giorni lavorativi"
            }
        )

# Insurance Provider Factory
class InsuranceProviderFactory:
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth_manager = auth_manager
    
    def get_provider(self, provider: InsuranceProvider) -> BaseInsuranceProvider:
        if provider == InsuranceProvider.ALLIANZ:
            return AllianzProvider(provider, self.auth_manager)
        elif provider == InsuranceProvider.UNIPOLSAI:
            return UnipolProvider(provider, self.auth_manager)
        else:
            return BaseInsuranceProvider(provider, self.auth_manager)

# Utility Functions
def calculate_pdf_hash(pdf_content: bytes) -> str:
    """Calculate SHA256 hash of PDF content"""
    return hashlib.sha256(pdf_content).hexdigest()

def generate_claim_id() -> str:
    """Generate unique claim ID"""
    return f"CID-{int(datetime.utcnow().timestamp())}-{str(uuid.uuid4())[:8]}"

async def validate_cid_data(cid_data: Dict[str, Any]) -> bool:
    """Validate CID data structure"""
    required_fields = ["person_a", "person_b", "accident_details"]
    return all(field in cid_data for field in required_fields)

# Global instances
auth_manager = AuthenticationManager()
provider_factory = InsuranceProviderFactory(auth_manager)

# Routes
@api_router.get("/")
async def root():
    return {"message": "CID Insurance Integration System API"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@api_router.post("/cid/submit", response_model=Dict[str, Any])
async def submit_cid(submission: CIDSubmission):
    """Submit CID to insurance companies"""
    try:
        # Validate CID data
        if not await validate_cid_data(submission.cid_data):
            raise HTTPException(status_code=400, detail="Invalid CID data structure")
        
        # Generate claim ID
        claim_id = generate_claim_id()
        
        # Extract PDF data
        pdf_base64 = submission.pdf_base64 or ""
        pdf_hash = submission.pdf_hash
        
        # If no hash provided, calculate from base64 data
        if not pdf_hash and pdf_base64:
            pdf_bytes = base64.b64decode(pdf_base64)
            pdf_hash = calculate_pdf_hash(pdf_bytes)
        
        # Get insurance providers from CID data
        person_a_provider = InsuranceProvider(submission.cid_data["person_a"]["insurance_company"])
        person_b_provider = InsuranceProvider(submission.cid_data["person_b"]["insurance_company"])
        
        api_responses = []
        
        # Determine submission strategy
        if person_a_provider == person_b_provider:
            # Same insurance company - single API call
            provider = provider_factory.get_provider(person_a_provider)
            response = await provider.submit_cid(submission.cid_data, pdf_base64, pdf_hash)
            api_responses.append(response)
        else:
            # Different companies - two API calls
            provider_a = provider_factory.get_provider(person_a_provider)
            provider_b = provider_factory.get_provider(person_b_provider)
            
            response_a = await provider_a.submit_cid(submission.cid_data, pdf_base64, pdf_hash)
            response_b = await provider_b.submit_cid(submission.cid_data, pdf_base64, pdf_hash)
            
            api_responses.extend([response_a, response_b])
        
        # Create CID record
        cid_record = CIDRecord(
            cid_data=submission.cid_data,
            pdf_hash=pdf_hash,
            pdf_base64=pdf_base64,
            claim_id=claim_id,
            status=CIDStatus.SUBMITTED,
            api_responses=api_responses
        )
        
        # Store in database
        await db.cid_records.insert_one(cid_record.dict())
        
        return {
            "success": True,
            "claim_id": claim_id,
            "message": "CID submitted successfully",
            "api_responses": [resp.dict() for resp in api_responses],
            "providers_contacted": len(api_responses)
        }
        
    except Exception as e:
        logger.error(f"Error submitting CID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.post("/cid/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF file and return base64 + hash"""
    try:
        # Validate file type
        if not file.content_type == "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Calculate hash
        pdf_hash = calculate_pdf_hash(content)
        
        # Convert to base64
        pdf_base64 = base64.b64encode(content).decode('utf-8')
        
        return {
            "filename": file.filename,
            "size": len(content),
            "hash": pdf_hash,
            "base64": pdf_base64,
            "content_type": file.content_type
        }
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@api_router.get("/cid/{claim_id}", response_model=Dict[str, Any])
async def get_cid_status(claim_id: str):
    """Get CID status by claim ID"""
    try:
        cid_record = await db.cid_records.find_one({"claim_id": claim_id}, {"_id": 0})
        if not cid_record:
            raise HTTPException(status_code=404, detail="CID not found")
        
        # Remove base64 data from response for performance
        cid_record_copy = dict(cid_record)
        cid_record_copy.pop("pdf_base64", None)
        
        return cid_record_copy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CID: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/cids", response_model=List[Dict[str, Any]])
async def get_all_cids():
    """Get all CID records (without PDF data)"""
    try:
        cids = await db.cid_records.find({}, {"pdf_base64": 0, "_id": 0}).to_list(1000)
        return cids
    except Exception as e:
        logger.error(f"Error retrieving CIDs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/providers")
async def get_supported_providers():
    """Get list of supported insurance providers"""
    return {
        "providers": [provider.value for provider in InsuranceProvider],
        "auth_methods": [method.value for method in AuthMethod],
        "total_providers": len(InsuranceProvider)
    }

# Mock insurance API endpoints for testing
@api_router.post("/mock/insurance/{provider}/submit")
async def mock_insurance_endpoint(provider: str, payload: Dict[str, Any]):
    """Mock insurance company API endpoint for testing"""
    claim_id = f"{provider.upper()}-{str(uuid.uuid4())[:8]}"
    
    return {
        "success": True,
        "claim_id": claim_id,
        "status": "received",
        "message": f"Mock response from {provider}",
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time": "2-5 business days"
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add missing import
import asyncio

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()