#!/usr/bin/env python3
"""
Comprehensive Backend Test Suite for CID Insurance Integration System
Tests all API endpoints and core functionality
"""

import requests
import json
import base64
import hashlib
import time
from datetime import datetime
from typing import Dict, Any
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / 'frontend' / '.env')

# Get backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

class CIDBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.claim_ids = []  # Store claim IDs for testing
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
        print()

    def create_sample_pdf_data(self) -> tuple:
        """Create sample PDF data for testing"""
        # Create a simple PDF-like content for testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
        
        # Calculate hash
        pdf_hash = hashlib.sha256(pdf_content).hexdigest()
        
        # Convert to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        return pdf_content, pdf_base64, pdf_hash

    def create_sample_cid_data(self, same_company: bool = True) -> Dict[str, Any]:
        """Create sample CID data for testing"""
        person_a_company = "allianz"
        person_b_company = "allianz" if same_company else "unipolsai"
        
        return {
            "person_a": {
                "name": "Mario",
                "surname": "Rossi",
                "license_plate": "AB123CD",
                "insurance_company": person_a_company,
                "policy_number": "POL123456"
            },
            "person_b": {
                "name": "Luigi",
                "surname": "Bianchi", 
                "license_plate": "EF456GH",
                "insurance_company": person_b_company,
                "policy_number": "POL789012"
            },
            "accident_details": {
                "timestamp": "2024-01-15T10:30:00Z",
                "location": "Via Roma 123, Milano",
                "description": "Rear-end collision at traffic light",
                "circumstances": ["traffic_light", "rear_collision"],
                "damage_description": "Minor damage to rear bumper"
            }
        }

    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.session.get(f"{API_BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_test("Health Check", True, f"Status: {data['status']}")
                else:
                    self.log_test("Health Check", False, f"Invalid response format: {data}")
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")

    def test_get_providers(self):
        """Test get supported providers endpoint"""
        try:
            response = self.session.get(f"{API_BASE_URL}/providers")
            
            if response.status_code == 200:
                data = response.json()
                expected_providers = ["allianz", "unipolsai", "generali", "axa"]
                
                if "providers" in data and all(p in data["providers"] for p in expected_providers):
                    self.log_test("Get Providers", True, f"Found {len(data['providers'])} providers")
                else:
                    self.log_test("Get Providers", False, f"Missing expected providers: {data}")
            else:
                self.log_test("Get Providers", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get Providers", False, f"Exception: {str(e)}")

    def test_pdf_upload(self):
        """Test PDF upload endpoint"""
        try:
            pdf_content, pdf_base64, expected_hash = self.create_sample_pdf_data()
            
            # Create a temporary file-like object
            files = {
                'file': ('test.pdf', pdf_content, 'application/pdf')
            }
            
            response = self.session.post(f"{API_BASE_URL}/cid/upload-pdf", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if "hash" in data and data["hash"] == expected_hash:
                    self.log_test("PDF Upload", True, f"Hash matches: {data['hash'][:16]}...")
                    return data["base64"], data["hash"]
                else:
                    self.log_test("PDF Upload", False, f"Hash mismatch or missing: {data}")
            else:
                self.log_test("PDF Upload", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("PDF Upload", False, f"Exception: {str(e)}")
        
        return None, None

    def test_cid_submit_same_company(self):
        """Test CID submission with same insurance company"""
        try:
            cid_data = self.create_sample_cid_data(same_company=True)
            pdf_content, pdf_base64, pdf_hash = self.create_sample_pdf_data()
            
            payload = {
                "cid_data": cid_data,
                "pdf_base64": pdf_base64,
                "pdf_hash": pdf_hash
            }
            
            response = self.session.post(
                f"{API_BASE_URL}/cid/submit",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "claim_id" in data:
                    # Should make 1 API call for same company
                    if data.get("providers_contacted") == 1:
                        self.claim_ids.append(data["claim_id"])
                        self.log_test("CID Submit (Same Company)", True, 
                                    f"Claim ID: {data['claim_id']}, Providers: {data['providers_contacted']}")
                    else:
                        self.log_test("CID Submit (Same Company)", False, 
                                    f"Expected 1 provider, got {data.get('providers_contacted')}")
                else:
                    self.log_test("CID Submit (Same Company)", False, f"Invalid response: {data}")
            else:
                self.log_test("CID Submit (Same Company)", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("CID Submit (Same Company)", False, f"Exception: {str(e)}")

    def test_cid_submit_different_companies(self):
        """Test CID submission with different insurance companies"""
        try:
            cid_data = self.create_sample_cid_data(same_company=False)
            pdf_content, pdf_base64, pdf_hash = self.create_sample_pdf_data()
            
            payload = {
                "cid_data": cid_data,
                "pdf_base64": pdf_base64,
                "pdf_hash": pdf_hash
            }
            
            response = self.session.post(
                f"{API_BASE_URL}/cid/submit",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "claim_id" in data:
                    # Should make 2 API calls for different companies
                    if data.get("providers_contacted") == 2:
                        self.claim_ids.append(data["claim_id"])
                        self.log_test("CID Submit (Different Companies)", True, 
                                    f"Claim ID: {data['claim_id']}, Providers: {data['providers_contacted']}")
                    else:
                        self.log_test("CID Submit (Different Companies)", False, 
                                    f"Expected 2 providers, got {data.get('providers_contacted')}")
                else:
                    self.log_test("CID Submit (Different Companies)", False, f"Invalid response: {data}")
            else:
                self.log_test("CID Submit (Different Companies)", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("CID Submit (Different Companies)", False, f"Exception: {str(e)}")

    def test_cid_submit_invalid_data(self):
        """Test CID submission with invalid data"""
        try:
            # Missing required fields
            invalid_payload = {
                "cid_data": {
                    "person_a": {"name": "Test"}  # Missing required fields
                }
            }
            
            response = self.session.post(
                f"{API_BASE_URL}/cid/submit",
                json=invalid_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                self.log_test("CID Submit (Invalid Data)", True, "Correctly rejected invalid data")
            else:
                self.log_test("CID Submit (Invalid Data)", False, 
                            f"Expected 400, got {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("CID Submit (Invalid Data)", False, f"Exception: {str(e)}")

    def test_get_cid_status(self):
        """Test getting CID status by claim ID"""
        if not self.claim_ids:
            self.log_test("Get CID Status", False, "No claim IDs available for testing")
            return
            
        try:
            claim_id = self.claim_ids[0]
            response = self.session.get(f"{API_BASE_URL}/cid/{claim_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "claim_id" in data and data["claim_id"] == claim_id:
                    self.log_test("Get CID Status", True, f"Retrieved CID: {claim_id}")
                else:
                    self.log_test("Get CID Status", False, f"Invalid response: {data}")
            else:
                self.log_test("Get CID Status", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get CID Status", False, f"Exception: {str(e)}")

    def test_get_cid_status_not_found(self):
        """Test getting CID status with non-existent claim ID"""
        try:
            fake_claim_id = "CID-NONEXISTENT-12345"
            response = self.session.get(f"{API_BASE_URL}/cid/{fake_claim_id}")
            
            if response.status_code == 404:
                self.log_test("Get CID Status (Not Found)", True, "Correctly returned 404 for non-existent CID")
            else:
                self.log_test("Get CID Status (Not Found)", False, 
                            f"Expected 404, got {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get CID Status (Not Found)", False, f"Exception: {str(e)}")

    def test_get_all_cids(self):
        """Test getting all CID records"""
        try:
            response = self.session.get(f"{API_BASE_URL}/cids")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get All CIDs", True, f"Retrieved {len(data)} CID records")
                else:
                    self.log_test("Get All CIDs", False, f"Expected list, got: {type(data)}")
            else:
                self.log_test("Get All CIDs", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Get All CIDs", False, f"Exception: {str(e)}")

    def test_mock_insurance_endpoints(self):
        """Test mock insurance provider endpoints"""
        providers = ["allianz", "unipolsai", "generali", "axa"]
        
        for provider in providers:
            try:
                payload = {
                    "test_data": "mock_submission",
                    "provider": provider
                }
                
                response = self.session.post(
                    f"{API_BASE_URL}/mock/insurance/{provider}/submit",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "claim_id" in data:
                        self.log_test(f"Mock Insurance ({provider.title()})", True, 
                                    f"Mock claim ID: {data['claim_id']}")
                    else:
                        self.log_test(f"Mock Insurance ({provider.title()})", False, 
                                    f"Invalid response: {data}")
                else:
                    self.log_test(f"Mock Insurance ({provider.title()})", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Mock Insurance ({provider.title()})", False, f"Exception: {str(e)}")

    def test_claim_id_format(self):
        """Test claim ID format validation"""
        if not self.claim_ids:
            self.log_test("Claim ID Format", False, "No claim IDs available for testing")
            return
            
        try:
            claim_id = self.claim_ids[0]
            # Expected format: CID-timestamp-uuid
            parts = claim_id.split('-')
            
            if len(parts) >= 3 and parts[0] == "CID":
                # Check if second part is numeric (timestamp)
                try:
                    int(parts[1])
                    self.log_test("Claim ID Format", True, f"Valid format: {claim_id}")
                except ValueError:
                    self.log_test("Claim ID Format", False, f"Invalid timestamp in: {claim_id}")
            else:
                self.log_test("Claim ID Format", False, f"Invalid format: {claim_id}")
                
        except Exception as e:
            self.log_test("Claim ID Format", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("CID Insurance Integration System - Backend Test Suite")
        print("=" * 60)
        print(f"Testing against: {API_BASE_URL}")
        print()
        
        # Basic endpoint tests
        self.test_health_check()
        self.test_get_providers()
        
        # PDF processing tests
        self.test_pdf_upload()
        
        # CID submission tests
        self.test_cid_submit_same_company()
        self.test_cid_submit_different_companies()
        self.test_cid_submit_invalid_data()
        
        # CID retrieval tests
        self.test_get_cid_status()
        self.test_get_cid_status_not_found()
        self.test_get_all_cids()
        
        # Mock insurance tests
        self.test_mock_insurance_endpoints()
        
        # Format validation tests
        self.test_claim_id_format()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        print()
        
        if failed > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['details']}")
            print()
        
        print("DETAILED RESULTS:")
        for result in self.test_results:
            print(f"{result['status']} - {result['test']}")
            if result['details']:
                print(f"    {result['details']}")

if __name__ == "__main__":
    tester = CIDBackendTester()
    tester.run_all_tests()