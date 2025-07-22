#!/usr/bin/env python3
"""
Additional verification tests for specific CID Insurance Integration System features
"""

import requests
import json
import base64
import hashlib
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

def test_modular_provider_system():
    """Test that all 4 insurance providers are supported"""
    print("Testing Modular Provider System...")
    
    response = requests.get(f"{API_BASE_URL}/providers")
    if response.status_code == 200:
        data = response.json()
        expected_providers = ["allianz", "unipolsai", "generali", "axa"]
        
        if all(provider in data["providers"] for provider in expected_providers):
            print("✅ All 4 insurance providers supported: Allianz, UnipolSai, Generali, AXA")
            return True
        else:
            print(f"❌ Missing providers. Found: {data['providers']}")
            return False
    else:
        print(f"❌ Failed to get providers: {response.status_code}")
        return False

def test_same_vs_different_company_routing():
    """Test routing logic for same vs different insurance companies"""
    print("\nTesting Same vs Different Company Routing...")
    
    # Create sample PDF data
    pdf_content = b"%PDF-1.4\nSample PDF content for testing"
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    pdf_hash = hashlib.sha256(pdf_content).hexdigest()
    
    # Test 1: Same company (should make 1 API call)
    same_company_data = {
        "cid_data": {
            "person_a": {
                "name": "Marco",
                "surname": "Verdi",
                "license_plate": "AB123CD",
                "insurance_company": "allianz",
                "policy_number": "POL111111"
            },
            "person_b": {
                "name": "Paolo",
                "surname": "Neri",
                "license_plate": "EF456GH",
                "insurance_company": "allianz",  # Same company
                "policy_number": "POL222222"
            },
            "accident_details": {
                "timestamp": "2024-01-15T10:30:00Z",
                "location": "Via Milano 456, Roma",
                "description": "Side collision at intersection",
                "circumstances": ["intersection", "side_collision"],
                "damage_description": "Damage to left side door"
            }
        },
        "pdf_base64": pdf_base64,
        "pdf_hash": pdf_hash
    }
    
    response = requests.post(f"{API_BASE_URL}/cid/submit", json=same_company_data)
    if response.status_code == 200:
        data = response.json()
        if data.get("providers_contacted") == 1:
            print("✅ Same company routing: 1 API call made")
            same_test_passed = True
        else:
            print(f"❌ Same company routing failed: {data.get('providers_contacted')} calls made")
            same_test_passed = False
    else:
        print(f"❌ Same company test failed: {response.status_code}")
        same_test_passed = False
    
    # Test 2: Different companies (should make 2 API calls)
    different_company_data = {
        "cid_data": {
            "person_a": {
                "name": "Anna",
                "surname": "Rossi",
                "license_plate": "GH789IJ",
                "insurance_company": "generali",
                "policy_number": "POL333333"
            },
            "person_b": {
                "name": "Luca",
                "surname": "Bianchi",
                "license_plate": "KL012MN",
                "insurance_company": "axa",  # Different company
                "policy_number": "POL444444"
            },
            "accident_details": {
                "timestamp": "2024-01-16T14:15:00Z",
                "location": "Corso Italia 789, Napoli",
                "description": "Rear-end collision in traffic",
                "circumstances": ["traffic", "rear_collision"],
                "damage_description": "Damage to front and rear bumpers"
            }
        },
        "pdf_base64": pdf_base64,
        "pdf_hash": pdf_hash
    }
    
    response = requests.post(f"{API_BASE_URL}/cid/submit", json=different_company_data)
    if response.status_code == 200:
        data = response.json()
        if data.get("providers_contacted") == 2:
            print("✅ Different companies routing: 2 API calls made")
            different_test_passed = True
        else:
            print(f"❌ Different companies routing failed: {data.get('providers_contacted')} calls made")
            different_test_passed = False
    else:
        print(f"❌ Different companies test failed: {response.status_code}")
        different_test_passed = False
    
    return same_test_passed and different_test_passed

def test_pdf_processing_and_hashing():
    """Test PDF processing and SHA256 hashing"""
    print("\nTesting PDF Processing and SHA256 Hashing...")
    
    # Create test PDF content
    test_content = b"%PDF-1.4\nTest PDF content with numbers: 12345"
    expected_hash = hashlib.sha256(test_content).hexdigest()
    
    # Test multipart upload
    files = {'file': ('test_document.pdf', test_content, 'application/pdf')}
    response = requests.post(f"{API_BASE_URL}/cid/upload-pdf", files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("hash") == expected_hash:
            print(f"✅ PDF hash calculation correct: {expected_hash[:16]}...")
            
            # Verify base64 encoding
            decoded_content = base64.b64decode(data.get("base64", ""))
            if decoded_content == test_content:
                print("✅ PDF base64 encoding/decoding correct")
                return True
            else:
                print("❌ PDF base64 encoding/decoding failed")
                return False
        else:
            print(f"❌ Hash mismatch. Expected: {expected_hash}, Got: {data.get('hash')}")
            return False
    else:
        print(f"❌ PDF upload failed: {response.status_code}")
        return False

def run_verification_tests():
    """Run all verification tests"""
    print("=" * 70)
    print("CID Insurance Integration System - Feature Verification Tests")
    print("=" * 70)
    
    tests = [
        ("Modular Provider System", test_modular_provider_system),
        ("Same vs Different Company Routing", test_same_vs_different_company_routing),
        ("PDF Processing and Hashing", test_pdf_processing_and_hashing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("FEATURE VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Total Features Tested: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print()
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

if __name__ == "__main__":
    run_verification_tests()