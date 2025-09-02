#!/usr/bin/env python3
"""
Comprehensive Backend Testing for MRI Noise Masking API
Tests all backend endpoints for the MRI noise masking application
"""

import requests
import json
import os
from datetime import datetime
import time

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    base_url = line.split('=')[1].strip()
                    return f"{base_url}/api"
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
    return "http://localhost:8001/api"  # fallback

BASE_URL = get_backend_url()
print(f"Testing backend at: {BASE_URL}")

class MRIBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message="", data=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        
    def test_health_check(self):
        """Test basic API health check"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "MRI Noise Masking API" in data.get("message", ""):
                    self.log_test("Health Check", True, "API is responding correctly")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected response: {data}")
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
        return False
    
    def test_mri_patterns_get_all(self):
        """Test GET /api/mri-patterns - should return default patterns"""
        try:
            response = self.session.get(f"{self.base_url}/mri-patterns")
            if response.status_code == 200:
                patterns = response.json()
                if len(patterns) >= 3:  # Should have at least 3 default patterns
                    # Check for expected default patterns
                    pattern_names = [p["name"] for p in patterns]
                    expected_patterns = ["Brain T1 Weighted", "Spine MRI", "Knee Joint"]
                    
                    found_patterns = [name for name in expected_patterns if name in pattern_names]
                    if len(found_patterns) == 3:
                        # Verify pattern structure
                        sample_pattern = patterns[0]
                        required_fields = ["id", "name", "duration_minutes", "noise_frequency_hz", 
                                         "noise_intensity_db", "sequence_pattern"]
                        
                        if all(field in sample_pattern for field in required_fields):
                            self.log_test("MRI Patterns - Get All", True, 
                                        f"Found {len(patterns)} patterns with correct structure")
                            return patterns
                        else:
                            missing = [f for f in required_fields if f not in sample_pattern]
                            self.log_test("MRI Patterns - Get All", False, 
                                        f"Missing fields: {missing}")
                    else:
                        self.log_test("MRI Patterns - Get All", False, 
                                    f"Missing default patterns. Found: {found_patterns}")
                else:
                    self.log_test("MRI Patterns - Get All", False, 
                                f"Expected at least 3 patterns, got {len(patterns)}")
            else:
                self.log_test("MRI Patterns - Get All", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("MRI Patterns - Get All", False, f"Error: {str(e)}")
        return None
    
    def test_mri_pattern_get_specific(self, pattern_id):
        """Test GET /api/mri-patterns/{id}"""
        try:
            response = self.session.get(f"{self.base_url}/mri-patterns/{pattern_id}")
            if response.status_code == 200:
                pattern = response.json()
                if pattern["id"] == pattern_id:
                    # Verify frequency/intensity data
                    if (pattern["noise_frequency_hz"] >= 1000 and 
                        pattern["noise_intensity_db"] >= 100 and
                        len(pattern["sequence_pattern"]) > 0):
                        self.log_test("MRI Pattern - Get Specific", True, 
                                    f"Retrieved pattern: {pattern['name']}")
                        return pattern
                    else:
                        self.log_test("MRI Pattern - Get Specific", False, 
                                    "Invalid frequency/intensity data")
                else:
                    self.log_test("MRI Pattern - Get Specific", False, "ID mismatch")
            elif response.status_code == 404:
                self.log_test("MRI Pattern - Get Specific", True, 
                            "Correctly returned 404 for invalid ID")
                return None
            else:
                self.log_test("MRI Pattern - Get Specific", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("MRI Pattern - Get Specific", False, f"Error: {str(e)}")
        return None
    
    def test_mri_pattern_create(self):
        """Test POST /api/mri-patterns"""
        try:
            new_pattern = {
                "name": "Test Cardiac MRI",
                "duration_minutes": 20,
                "noise_frequency_hz": 1800,
                "noise_intensity_db": 115,
                "sequence_pattern": [
                    {"frequency": 1800, "duration": 600, "intensity": 115},
                    {"frequency": 2000, "duration": 600, "intensity": 118}
                ]
            }
            
            response = self.session.post(f"{self.base_url}/mri-patterns", 
                                       json=new_pattern)
            if response.status_code == 200:
                created_pattern = response.json()
                if (created_pattern["name"] == new_pattern["name"] and 
                    "id" in created_pattern):
                    self.log_test("MRI Pattern - Create", True, 
                                f"Created pattern with ID: {created_pattern['id']}")
                    return created_pattern
                else:
                    self.log_test("MRI Pattern - Create", False, "Invalid response data")
            else:
                self.log_test("MRI Pattern - Create", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("MRI Pattern - Create", False, f"Error: {str(e)}")
        return None
    
    def test_sound_profiles_get_all(self):
        """Test GET /api/sound-profiles - should return default sounds"""
        try:
            response = self.session.get(f"{self.base_url}/sound-profiles")
            if response.status_code == 200:
                profiles = response.json()
                if len(profiles) >= 5:  # Should have at least 5 default profiles
                    # Check for expected sound types
                    profile_names = [p["name"] for p in profiles]
                    expected_sounds = ["Ocean Waves", "White Noise", "Pink Noise"]
                    
                    found_sounds = [name for name in expected_sounds if name in profile_names]
                    if len(found_sounds) >= 2:
                        # Verify masking effectiveness structure
                        sample_profile = profiles[0]
                        if ("masking_effectiveness" in sample_profile and
                            "low_freq" in sample_profile["masking_effectiveness"] and
                            "mid_freq" in sample_profile["masking_effectiveness"] and
                            "high_freq" in sample_profile["masking_effectiveness"]):
                            self.log_test("Sound Profiles - Get All", True, 
                                        f"Found {len(profiles)} sound profiles with masking data")
                            return profiles
                        else:
                            self.log_test("Sound Profiles - Get All", False, 
                                        "Missing masking effectiveness data")
                    else:
                        self.log_test("Sound Profiles - Get All", False, 
                                    f"Missing expected sounds. Found: {found_sounds}")
                else:
                    self.log_test("Sound Profiles - Get All", False, 
                                f"Expected at least 5 profiles, got {len(profiles)}")
            else:
                self.log_test("Sound Profiles - Get All", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Sound Profiles - Get All", False, f"Error: {str(e)}")
        return None
    
    def test_sound_profile_get_specific(self, profile_id):
        """Test GET /api/sound-profiles/{id}"""
        try:
            response = self.session.get(f"{self.base_url}/sound-profiles/{profile_id}")
            if response.status_code == 200:
                profile = response.json()
                if profile["id"] == profile_id:
                    # Verify masking effectiveness values are reasonable (0-1 range)
                    effectiveness = profile["masking_effectiveness"]
                    if (0 <= effectiveness["low_freq"] <= 1 and
                        0 <= effectiveness["mid_freq"] <= 1 and
                        0 <= effectiveness["high_freq"] <= 1):
                        self.log_test("Sound Profile - Get Specific", True, 
                                    f"Retrieved profile: {profile['name']}")
                        return profile
                    else:
                        self.log_test("Sound Profile - Get Specific", False, 
                                    "Invalid masking effectiveness values")
                else:
                    self.log_test("Sound Profile - Get Specific", False, "ID mismatch")
            elif response.status_code == 404:
                self.log_test("Sound Profile - Get Specific", True, 
                            "Correctly returned 404 for invalid ID")
                return None
            else:
                self.log_test("Sound Profile - Get Specific", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Sound Profile - Get Specific", False, f"Error: {str(e)}")
        return None
    
    def test_sound_profile_create(self):
        """Test POST /api/sound-profiles"""
        try:
            new_profile = {
                "name": "Test Brown Noise",
                "type": "white_noise",
                "base_frequency_hz": 600,
                "masking_effectiveness": {
                    "low_freq": 0.95,
                    "mid_freq": 0.85,
                    "high_freq": 0.75
                },
                "file_path": "brown_noise.mp3"
            }
            
            response = self.session.post(f"{self.base_url}/sound-profiles", 
                                       json=new_profile)
            if response.status_code == 200:
                created_profile = response.json()
                if (created_profile["name"] == new_profile["name"] and 
                    "id" in created_profile):
                    self.log_test("Sound Profile - Create", True, 
                                f"Created profile with ID: {created_profile['id']}")
                    return created_profile
                else:
                    self.log_test("Sound Profile - Create", False, "Invalid response data")
            else:
                self.log_test("Sound Profile - Create", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Sound Profile - Create", False, f"Error: {str(e)}")
        return None
    
    def test_session_create(self, mri_pattern_id, sound_profile_id):
        """Test POST /api/sessions"""
        try:
            new_session = {
                "mri_pattern_id": mri_pattern_id,
                "sound_profile_id": sound_profile_id,
                "volume_level": 0.8
            }
            
            response = self.session.post(f"{self.base_url}/sessions", 
                                       json=new_session)
            if response.status_code == 200:
                session = response.json()
                if (session["mri_pattern_id"] == mri_pattern_id and
                    session["sound_profile_id"] == sound_profile_id and
                    "id" in session and
                    session["completed"] == False):
                    self.log_test("Session - Create", True, 
                                f"Created session with ID: {session['id']}")
                    return session
                else:
                    self.log_test("Session - Create", False, "Invalid session data")
            else:
                self.log_test("Session - Create", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Session - Create", False, f"Error: {str(e)}")
        return None
    
    def test_session_create_invalid_ids(self):
        """Test POST /api/sessions with invalid IDs"""
        try:
            invalid_session = {
                "mri_pattern_id": "invalid-id",
                "sound_profile_id": "invalid-id",
                "volume_level": 0.8
            }
            
            response = self.session.post(f"{self.base_url}/sessions", 
                                       json=invalid_session)
            if response.status_code == 400:
                self.log_test("Session - Create Invalid IDs", True, 
                            "Correctly rejected invalid IDs with 400 error")
                return True
            else:
                self.log_test("Session - Create Invalid IDs", False, 
                            f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_test("Session - Create Invalid IDs", False, f"Error: {str(e)}")
        return False
    
    def test_session_get(self, session_id):
        """Test GET /api/sessions/{id}"""
        try:
            response = self.session.get(f"{self.base_url}/sessions/{session_id}")
            if response.status_code == 200:
                session = response.json()
                if session["id"] == session_id:
                    self.log_test("Session - Get", True, 
                                f"Retrieved session: {session_id}")
                    return session
                else:
                    self.log_test("Session - Get", False, "ID mismatch")
            elif response.status_code == 404:
                self.log_test("Session - Get", True, 
                            "Correctly returned 404 for invalid session ID")
                return None
            else:
                self.log_test("Session - Get", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Session - Get", False, f"Error: {str(e)}")
        return None
    
    def test_session_complete(self, session_id):
        """Test PUT /api/sessions/{id}/complete"""
        try:
            # Test with comfort rating
            response = self.session.put(f"{self.base_url}/sessions/{session_id}/complete",
                                      params={"comfort_rating": 8})
            if response.status_code == 200:
                result = response.json()
                if "message" in result and "completed" in result["message"]:
                    self.log_test("Session - Complete", True, 
                                "Successfully completed session with comfort rating")
                    return True
                else:
                    self.log_test("Session - Complete", False, "Invalid response message")
            else:
                self.log_test("Session - Complete", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Session - Complete", False, f"Error: {str(e)}")
        return False
    
    def test_session_complete_invalid_rating(self, session_id):
        """Test PUT /api/sessions/{id}/complete with invalid rating"""
        try:
            response = self.session.put(f"{self.base_url}/sessions/{session_id}/complete",
                                      params={"comfort_rating": 15})  # Invalid rating > 10
            if response.status_code == 400:
                self.log_test("Session - Complete Invalid Rating", True, 
                            "Correctly rejected invalid comfort rating")
                return True
            else:
                self.log_test("Session - Complete Invalid Rating", False, 
                            f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_test("Session - Complete Invalid Rating", False, f"Error: {str(e)}")
        return False
    
    def test_masking_effectiveness(self, mri_pattern_id, sound_profile_id):
        """Test GET /api/masking-effectiveness/{mri_id}/{sound_id}"""
        try:
            response = self.session.get(f"{self.base_url}/masking-effectiveness/{mri_pattern_id}/{sound_profile_id}")
            if response.status_code == 200:
                effectiveness = response.json()
                required_fields = ["effectiveness_score", "mri_frequency", "sound_type", "recommended_volume"]
                
                if all(field in effectiveness for field in required_fields):
                    # Verify frequency range logic
                    score = effectiveness["effectiveness_score"]
                    freq = effectiveness["mri_frequency"]
                    volume = effectiveness["recommended_volume"]
                    
                    if (0 <= score <= 1 and 
                        freq > 0 and 
                        0 <= volume <= 1):
                        
                        # Test frequency categorization
                        if freq < 1000:
                            category = "low frequency"
                        elif freq < 3000:
                            category = "mid frequency"
                        else:
                            category = "high frequency"
                        
                        self.log_test("Masking Effectiveness", True, 
                                    f"Score: {score:.2f}, Freq: {freq}Hz ({category}), Volume: {volume:.2f}")
                        return effectiveness
                    else:
                        self.log_test("Masking Effectiveness", False, 
                                    "Invalid effectiveness values")
                else:
                    missing = [f for f in required_fields if f not in effectiveness]
                    self.log_test("Masking Effectiveness", False, 
                                f"Missing fields: {missing}")
            else:
                self.log_test("Masking Effectiveness", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Masking Effectiveness", False, f"Error: {str(e)}")
        return None
    
    def test_masking_effectiveness_invalid_ids(self):
        """Test masking effectiveness with invalid IDs"""
        try:
            response = self.session.get(f"{self.base_url}/masking-effectiveness/invalid-id/invalid-id")
            if response.status_code == 404:
                self.log_test("Masking Effectiveness - Invalid IDs", True, 
                            "Correctly returned 404 for invalid IDs")
                return True
            else:
                self.log_test("Masking Effectiveness - Invalid IDs", False, 
                            f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_test("Masking Effectiveness - Invalid IDs", False, f"Error: {str(e)}")
        return False
    
    def run_comprehensive_tests(self):
        """Run all backend tests in sequence"""
        print("=" * 60)
        print("MRI NOISE MASKING BACKEND API TESTS")
        print("=" * 60)
        
        # 1. Health Check
        if not self.test_health_check():
            print("❌ API is not responding. Stopping tests.")
            return False
        
        # 2. MRI Pattern Tests
        print("\n--- MRI Pattern Management Tests ---")
        patterns = self.test_mri_patterns_get_all()
        if patterns:
            # Test getting specific pattern
            first_pattern = patterns[0]
            self.test_mri_pattern_get_specific(first_pattern["id"])
            
            # Test invalid pattern ID
            self.test_mri_pattern_get_specific("invalid-pattern-id")
        
        # Test creating new pattern
        created_pattern = self.test_mri_pattern_create()
        
        # 3. Sound Profile Tests
        print("\n--- Sound Profile Management Tests ---")
        sound_profiles = self.test_sound_profiles_get_all()
        if sound_profiles:
            # Test getting specific profile
            first_profile = sound_profiles[0]
            self.test_sound_profile_get_specific(first_profile["id"])
            
            # Test invalid profile ID
            self.test_sound_profile_get_specific("invalid-profile-id")
        
        # Test creating new profile
        created_profile = self.test_sound_profile_create()
        
        # 4. Session Management Tests
        print("\n--- Session Management Tests ---")
        if patterns and sound_profiles:
            # Test creating session with valid IDs
            session = self.test_session_create(patterns[0]["id"], sound_profiles[0]["id"])
            
            if session:
                # Test getting session
                self.test_session_get(session["id"])
                
                # Test completing session
                self.test_session_complete(session["id"])
                
                # Test invalid comfort rating (create another session first)
                session2 = self.test_session_create(patterns[0]["id"], sound_profiles[0]["id"])
                if session2:
                    self.test_session_complete_invalid_rating(session2["id"])
        
        # Test session creation with invalid IDs
        self.test_session_create_invalid_ids()
        
        # Test getting invalid session
        self.test_session_get("invalid-session-id")
        
        # 5. Masking Effectiveness Tests
        print("\n--- Masking Effectiveness Tests ---")
        if patterns and sound_profiles:
            # Test effectiveness calculation
            self.test_masking_effectiveness(patterns[0]["id"], sound_profiles[0]["id"])
            
            # Test with different frequency ranges
            for pattern in patterns[:3]:  # Test first 3 patterns
                for profile in sound_profiles[:2]:  # Test first 2 profiles
                    self.test_masking_effectiveness(pattern["id"], profile["id"])
        
        # Test with invalid IDs
        self.test_masking_effectiveness_invalid_ids()
        
        # 6. Summary
        self.print_test_summary()
        return True
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n--- FAILED TESTS ---")
            for result in self.test_results:
                if not result["success"]:
                    print(f"❌ {result['test']}: {result['message']}")
        
        print("\n--- CRITICAL FUNCTIONALITY STATUS ---")
        
        # Check critical functionality
        critical_tests = {
            "API Health": any("Health Check" in r["test"] and r["success"] for r in self.test_results),
            "MRI Patterns": any("MRI Patterns - Get All" in r["test"] and r["success"] for r in self.test_results),
            "Sound Profiles": any("Sound Profiles - Get All" in r["test"] and r["success"] for r in self.test_results),
            "Session Creation": any("Session - Create" in r["test"] and r["success"] for r in self.test_results),
            "Masking Calculation": any("Masking Effectiveness" in r["test"] and r["success"] for r in self.test_results)
        }
        
        for functionality, status in critical_tests.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {functionality}")
        
        # Overall assessment
        critical_working = sum(critical_tests.values())
        if critical_working == len(critical_tests):
            print("\n🎉 ALL CRITICAL BACKEND FUNCTIONALITY IS WORKING")
        elif critical_working >= 4:
            print("\n⚠️  MOST CRITICAL FUNCTIONALITY IS WORKING")
        else:
            print("\n🚨 CRITICAL BACKEND ISSUES DETECTED")

if __name__ == "__main__":
    tester = MRIBackendTester()
    tester.run_comprehensive_tests()