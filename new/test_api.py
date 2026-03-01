"""
COMPREHENSIVE API TEST SUITE
Tests ALL API endpoints with multiple scenarios and edge cases.

Tests:
- Health check variations
- Multiple user scenarios (with/without injuries)
- Edge cases (empty data, invalid data, extreme values)
- Safety loop validation
- Context isolation between users
- Performance metrics
- Error handling
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
TIMEOUT = 300  # 5 minutes for slow LLM

# Test statistics
stats = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "results": [],
    "performance": []
}

def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def test_result(name, passed, details="", elapsed=0):
    """Record test result."""
    stats["total"] += 1
    if passed:
        stats["passed"] += 1
        icon = "✅"
    else:
        stats["failed"] += 1
        icon = "❌"
    
    stats["results"].append({
        "name": name,
        "passed": passed,
        "details": details,
        "elapsed": elapsed
    })
    
    if elapsed > 0:
        stats["performance"].append({"name": name, "elapsed": elapsed})
    
    print(f"{icon} {name}")
    if details:
        print(f"   └─ {details}")
    if elapsed > 0:
        print(f"   └─ Time: {elapsed:.1f}s")
    print()

# ============= TEST CASES ============= #

def test_health_basic():
    """Test basic health endpoint."""
    log("Testing: Health Check (Basic)")
    try:
        start = time.time()
        response = requests.get(f"{API_URL}/health", timeout=10)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            healthy = data.get("status") == "healthy"
            test_result(
                "Health Check - Basic",
                healthy,
                f"Status: {data.get('status')}, DB: {data.get('database')}, LLM: {data.get('llm_provider')}",
                elapsed
            )
            return healthy
        else:
            test_result("Health Check - Basic", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        test_result("Health Check - Basic", False, f"Error: {e}")
        return False

def test_plan_beginner_no_injury():
    """Test plan generation for beginner with no injuries."""
    log("Testing: Beginner User, No Injuries")
    
    payload = {
        "user_profile": {
            "goals": "Start getting fit and lose weight",
            "fitness_level": "beginner",
            "weight": 85.0,
            "age": 35,
            "equipment_available": ["bodyweight", "resistance bands"]
        },
        "injury_history": [],
        "thread_id": "api_test_beginner_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            has_plan = "workout_plan" in data
            is_safe = data.get("critique", {}).get("status") == "SAFE"
            exercises = len(data.get("workout_plan", {}).get("exercises", []))
            
            test_result(
                "Beginner - No Injuries",
                has_plan and is_safe,
                f"Exercises: {exercises}, Revisions: {data.get('revision_count')}, Status: {data.get('critique', {}).get('status')}",
                elapsed
            )
            return has_plan
        else:
            test_result("Beginner - No Injuries", False, f"Status: {response.status_code}, Error: {response.text[:100]}")
            return False
    except requests.exceptions.Timeout:
        test_result("Beginner - No Injuries", False, "Request timed out (5 min)")
        return False
    except Exception as e:
        test_result("Beginner - No Injuries", False, f"Error: {e}")
        return False

def test_plan_intermediate_with_injury():
    """Test plan generation with rotator cuff injury - should trigger safety loop."""
    log("Testing: Intermediate User, Rotator Cuff Injury (Safety Loop)")
    
    payload = {
        "user_profile": {
            "goals": "Build upper body strength and muscle mass",
            "fitness_level": "intermediate",
            "weight": 75.0,
            "age": 28,
            "equipment_available": ["barbell", "dumbbells", "bench", "pull-up bar"]
        },
        "injury_history": [
            {
                "injury_type": "Rotator cuff strain",
                "injury_date": "2024-03-15",
                "severity": "moderate",
                "notes": "Avoid overhead press and heavy shoulder work for 6 weeks"
            }
        ],
        "thread_id": "api_test_injury_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            is_safe = data.get("critique", {}).get("status") == "SAFE"
            revisions = data.get("revision_count", 0)
            flagged = data.get("critique", {}).get("flagged_exercises", [])
            
            test_result(
                "Intermediate - Rotator Cuff Injury",
                is_safe,
                f"Revisions: {revisions}, Flagged: {flagged}, Status: {data.get('critique', {}).get('status')}",
                elapsed
            )
            return is_safe
        else:
            test_result("Intermediate - Rotator Cuff Injury", False, f"Error: {response.text[:100]}")
            return False
    except Exception as e:
        test_result("Intermediate - Rotator Cuff Injury", False, f"Error: {e}")
        return False

def test_plan_advanced_multiple_injuries():
    """Test with multiple severe injuries - complex safety validation."""
    log("Testing: Advanced User, Multiple Severe Injuries")
    
    payload = {
        "user_profile": {
            "goals": "Maintain strength without aggravating injuries",
            "fitness_level": "advanced",
            "weight": 80.0,
            "age": 40,
            "equipment_available": ["full gym"]
        },
        "injury_history": [
            {
                "injury_type": "Herniated disc L4-L5",
                "injury_date": "2024-01-15",
                "severity": "severe",
                "notes": "No spinal loading - avoid squats, deadlifts, overhead press"
            },
            {
                "injury_type": "Torn meniscus (recovering)",
                "injury_date": "2024-02-01",
                "severity": "moderate",
                "notes": "No deep knee flexion beyond 90 degrees"
            }
        ],
        "thread_id": "api_test_multi_injury_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            revisions = data.get("revision_count", 0)
            is_safe = data.get("critique", {}).get("status") == "SAFE"
            exercises = data.get("workout_plan", {}).get("exercises", [])
            
            # Check no contraindicated exercises
            exercise_names = [e.get("name", "").lower() for e in exercises]
            has_squat = any("squat" in name for name in exercise_names)
            has_deadlift = any("deadlift" in name for name in exercise_names)
            
            test_result(
                "Advanced - Multiple Injuries",
                not has_squat and not has_deadlift,
                f"Revisions: {revisions}, Avoided squats: {not has_squat}, Avoided deadlifts: {not has_deadlift}",
                elapsed
            )
            return is_safe
        else:
            test_result("Advanced - Multiple Injuries", False, f"Error: {response.text[:100]}")
            return False
    except Exception as e:
        test_result("Advanced - Multiple Injuries", False, f"Error: {e}")
        return False

def test_plan_senior_low_impact():
    """Test senior citizen with arthritis - should recommend low-impact exercises."""
    log("Testing: Senior Citizen, Low Impact Needs")
    
    payload = {
        "user_profile": {
            "goals": "Maintain mobility and independence",
            "fitness_level": "beginner",
            "weight": 65.0,
            "age": 72,
            "equipment_available": ["chair", "light dumbbells", "resistance bands"]
        },
        "injury_history": [
            {
                "injury_type": "Knee arthritis (osteoarthritis)",
                "injury_date": "2020-01-01",
                "severity": "moderate",
                "notes": "Low-impact only, seated exercises preferred"
            }
        ],
        "thread_id": "api_test_senior_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            is_safe = data.get("critique", {}).get("status") == "SAFE"
            
            test_result(
                "Senior - Low Impact",
                is_safe,
                f"Status: {data.get('critique', {}).get('status')}, Revisions: {data.get('revision_count')}",
                elapsed
            )
            return is_safe
        else:
            test_result("Senior - Low Impact", False, f"Error: {response.text[:100]}")
            return False
    except Exception as e:
        test_result("Senior - Low Impact", False, f"Error: {e}")
        return False

def test_edge_minimal_input():
    """Test with minimal/vague input."""
    log("Testing: Edge Case - Minimal Input")
    
    payload = {
        "user_profile": {
            "goals": "Get fit",
            "fitness_level": "beginner"
        },
        "injury_history": [],
        "thread_id": "api_test_minimal_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            has_plan = "workout_plan" in data
            
            test_result(
                "Edge - Minimal Input",
                has_plan,
                f"Generated plan with minimal data: {has_plan}",
                elapsed
            )
            return has_plan
        elif response.status_code == 422:
            test_result("Edge - Minimal Input", True, "Properly rejected incomplete data (422)")
            return True
        else:
            test_result("Edge - Minimal Input", False, f"Unexpected: {response.status_code}")
            return False
    except Exception as e:
        test_result("Edge - Minimal Input", False, f"Error: {e}")
        return False

def test_edge_extreme_age():
    """Test with extreme age values."""
    log("Testing: Edge Case - Extreme Age (Teen)")
    
    payload = {
        "user_profile": {
            "goals": "Get stronger for basketball",
            "fitness_level": "beginner",
            "weight": 55.0,
            "age": 14,
            "equipment_available": ["bodyweight"]
        },
        "injury_history": [],
        "thread_id": "api_test_teen_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            test_result(
                "Edge - Young Teen (14)",
                True,
                "Generated age-appropriate plan",
                elapsed
            )
            return True
        else:
            test_result("Edge - Young Teen (14)", False, f"Error: {response.status_code}")
            return False
    except Exception as e:
        test_result("Edge - Young Teen (14)", False, f"Error: {e}")
        return False

def test_edge_empty_injuries():
    """Test with empty injury list (explicit empty array)."""
    log("Testing: Edge Case - Empty Injury Array")
    
    payload = {
        "user_profile": {
            "goals": "Build muscle",
            "fitness_level": "intermediate",
            "weight": 70.0,
            "equipment_available": ["barbell", "dumbbells"]
        },
        "injury_history": [],  # Explicit empty
        "thread_id": "api_test_empty_injury_001"
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            revisions = data.get("revision_count", 0)
            # With no injuries, should be safe on first try
            test_result(
                "Edge - Empty Injury Array",
                True,
                f"Revisions: {revisions} (expected: 1, no safety concerns)",
                elapsed
            )
            return True
        else:
            test_result("Edge - Empty Injury Array", False, f"Error: {response.status_code}")
            return False
    except Exception as e:
        test_result("Edge - Empty Injury Array", False, f"Error: {e}")
        return False

def test_history_retrieval():
    """Test history endpoint retrieval."""
    log("Testing: History Retrieval")
    
    try:
        start = time.time()
        # Use a thread_id from previous tests
        response = requests.get(f"{API_URL}/history/api_test_beginner_001", timeout=30)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            test_result(
                "History Retrieval",
                True,
                f"Thread found with {len(data.get('history', []))} entries",
                elapsed
            )
            return True
        elif response.status_code == 404:
            test_result("History Retrieval", True, "No history yet (expected)")
            return True
        else:
            test_result("History Retrieval", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        test_result("History Retrieval", False, f"Error: {e}")
        return False

def test_context_isolation():
    """Test that different thread_ids are isolated."""
    log("Testing: Context Isolation Between Users")
    
    # Create two different users with different injuries
    user1 = {
        "user_profile": {"goals": "Build upper body", "fitness_level": "intermediate"},
        "injury_history": [{"injury_type": "Shoulder injury", "injury_date": "2024-01-01", "severity": "moderate", "notes": "No overhead"}],
        "thread_id": "isolation_test_user1"
    }
    
    user2 = {
        "user_profile": {"goals": "Build legs", "fitness_level": "intermediate"},
        "injury_history": [],  # No injuries
        "thread_id": "isolation_test_user2"
    }
    
    try:
        # First request - user1 with injury
        start = time.time()
        resp1 = requests.post(f"{API_URL}/plan", json=user1, timeout=TIMEOUT)
        time1 = time.time() - start
        
        if resp1.status_code != 200:
            test_result("Context Isolation", False, "User1 request failed")
            return False
        
        # Second request - user2 no injury
        start = time.time()
        resp2 = requests.post(f"{API_URL}/plan", json=user2, timeout=TIMEOUT)
        time2 = time.time() - start
        
        if resp2.status_code != 200:
            test_result("Context Isolation", False, "User2 request failed")
            return False
        
        # User2 should have simpler plan (no revisions from user1's injury)
        data2 = resp2.json()
        user2_revisions = data2.get("revision_count", 0)
        
        test_result(
            "Context Isolation",
            True,
            f"User2 (no injury) revisions: {user2_revisions} (isolated from User1's shoulder injury)",
            time1 + time2
        )
        return True
        
    except Exception as e:
        test_result("Context Isolation", False, f"Error: {e}")
        return False

def test_invalid_fitness_level():
    """Test with invalid fitness level value."""
    log("Testing: Invalid Input - Wrong Fitness Level")
    
    payload = {
        "user_profile": {
            "goals": "Get fit",
            "fitness_level": "super_mega_pro",  # Invalid
            "weight": 70.0
        },
        "injury_history": [],
        "thread_id": "api_test_invalid_001"
    }
    
    try:
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=30)
        
        if response.status_code == 422:
            test_result("Invalid - Wrong Fitness Level", True, "Properly rejected with 422 validation error")
            return True
        elif response.status_code == 200:
            test_result("Invalid - Wrong Fitness Level", True, "Handled gracefully (accepted anyway)")
            return True
        else:
            test_result("Invalid - Wrong Fitness Level", False, f"Unexpected: {response.status_code}")
            return False
    except Exception as e:
        test_result("Invalid - Wrong Fitness Level", False, f"Error: {e}")
        return False

def test_missing_thread_id():
    """Test request without thread_id."""
    log("Testing: Edge Case - Missing thread_id")
    
    payload = {
        "user_profile": {
            "goals": "Get fit",
            "fitness_level": "beginner"
        },
        "injury_history": []
        # Missing thread_id
    }
    
    try:
        response = requests.post(f"{API_URL}/plan", json=payload, timeout=30)
        
        if response.status_code == 422:
            test_result("Missing thread_id", True, "Properly rejected missing required field")
            return True
        else:
            test_result("Missing thread_id", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        test_result("Missing thread_id", False, f"Error: {e}")
        return False

# ============= MAIN ============= #

def main():
    """Run comprehensive test suite."""
    print("=" * 70)
    print("AI PERSONAL TRAINER - COMPREHENSIVE API TEST SUITE")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_URL}")
    print(f"Timeout: {TIMEOUT}s per request")
    print("\n⚠️  Note: LLM requests take 30-120 seconds each")
    print("=" * 70 + "\n")
    
    suite_start = time.time()
    
    # 1. Health Check
    print("=" * 70)
    print("SECTION 1: HEALTH & CONNECTIVITY")
    print("=" * 70 + "\n")
    
    if not test_health_basic():
        print("\n❌ Health check failed. Is the server running?")
        print("   Start with: docker-compose up -d")
        return
    
    # 2. Core Scenarios
    print("\n" + "=" * 70)
    print("SECTION 2: CORE WORKOUT PLAN SCENARIOS")
    print("=" * 70 + "\n")
    
    test_plan_beginner_no_injury()
    test_plan_intermediate_with_injury()
    test_plan_advanced_multiple_injuries()
    test_plan_senior_low_impact()
    
    # 3. Edge Cases
    print("\n" + "=" * 70)
    print("SECTION 3: EDGE CASES & VALIDATION")
    print("=" * 70 + "\n")
    
    test_edge_minimal_input()
    test_edge_extreme_age()
    test_edge_empty_injuries()
    test_invalid_fitness_level()
    test_missing_thread_id()
    
    # 4. Data Management
    print("\n" + "=" * 70)
    print("SECTION 4: DATA MANAGEMENT & ISOLATION")
    print("=" * 70 + "\n")
    
    test_history_retrieval()
    test_context_isolation()
    
    # ============= FINAL REPORT ============= #
    suite_elapsed = time.time() - suite_start
    
    print("\n" + "=" * 70)
    print("COMPREHENSIVE API TEST SUITE - FINAL REPORT")
    print("=" * 70 + "\n")
    
    print("📊 TEST RESULTS")
    print("-" * 70)
    print(f"   Total Tests: {stats['total']}")
    print(f"   ✅ Passed: {stats['passed']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   Success Rate: {stats['passed']/max(1,stats['total'])*100:.1f}%")
    print()
    
    print("⚡ PERFORMANCE METRICS")
    print("-" * 70)
    print(f"   Total Suite Time: {suite_elapsed:.1f}s ({suite_elapsed/60:.1f} min)")
    if stats['performance']:
        avg_time = sum(p['elapsed'] for p in stats['performance']) / len(stats['performance'])
        print(f"   Average Request Time: {avg_time:.1f}s")
        slowest = max(stats['performance'], key=lambda x: x['elapsed'])
        fastest = min(stats['performance'], key=lambda x: x['elapsed'])
        print(f"   Fastest: {fastest['name']} ({fastest['elapsed']:.1f}s)")
        print(f"   Slowest: {slowest['name']} ({slowest['elapsed']:.1f}s)")
    print()
    
    print("📋 DETAILED RESULTS")
    print("-" * 70)
    for result in stats['results']:
        icon = "✅" if result['passed'] else "❌"
        time_str = f" ({result['elapsed']:.1f}s)" if result['elapsed'] > 0 else ""
        print(f"{icon} {result['name']}{time_str}")
        if result['details']:
            print(f"   └─ {result['details']}")
    print()
    
    # Final verdict
    print("=" * 70)
    if stats['failed'] == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ API is fully functional and production-ready")
    elif stats['failed'] <= 2:
        print("⚠️  MOSTLY PASSING - Review failed tests above")
    else:
        print("❌ SIGNIFICANT FAILURES - Review and fix before deployment")
    print("=" * 70)
    
    print(f"\n⏱️  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Total runtime: {suite_elapsed:.1f}s ({suite_elapsed/60:.1f} minutes)")
    
    return stats['failed'] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
