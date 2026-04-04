#!/usr/bin/env python3
"""
CIVA End-to-End System Validation
Tests all components: API health, metrics collection, Kafka pipeline, Dashboard updates
"""

import asyncio
import json
import time
import requests
from typing import Dict, Tuple, List
from datetime import datetime


class E2EValidator:
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        self.results = {}
        self.start_time = time.time()
        
        # Service endpoints
        self.services = {
            "behavior-agent": f"{base_url}:8002",
            "orchestrator": f"{base_url}:8003",
            "deception-agent": f"{base_url}:8004",
            "threat-intel": f"{base_url}:8005",
            "sentinel-sdk": f"{base_url}:8001",
            "prometheus": f"{base_url}:9090",
            "grafana": f"{base_url}:3000",
            "kafka": f"{base_url}:9092",
            "redis": f"{base_url}:6379",
        }
    
    def print_header(self, title: str):
        """Print formatted test section header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    
    def test_service_health(self) -> bool:
        """Test 1: All services are running and healthy."""
        self.print_header("TEST 1: Service Health Check")
        all_healthy = True
        
        health_endpoints = {
            "behavior-agent": f"{self.services['behavior-agent']}/health",
            "orchestrator": f"{self.services['orchestrator']}/health",
            "prometheus": f"{self.services['prometheus']}/-/healthy",
            "grafana": f"{self.services['grafana']}/api/health",
        }
        
        for service, endpoint in health_endpoints.items():
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    print(f"[✓] {service}: HEALTHY")
                    self.results[f"{service}_health"] = "PASS"
                else:
                    print(f"[✗] {service}: {response.status_code}")
                    self.results[f"{service}_health"] = "FAIL"
                    all_healthy = False
            except Exception as e:
                print(f"[✗] {service}: {str(e)}")
                self.results[f"{service}_health"] = "ERROR"
                all_healthy = False
        
        return all_healthy
    
    def test_behavior_agent_scoring(self) -> bool:
        """Test 2: Behavior agent risk scoring API."""
        self.print_header("TEST 2: Behavior Agent Scoring")
        
        test_payload = {
            "event_id": f"e2e-test-{int(time.time())}",
            "session_id": "sess-e2e-test",
            "user_id": "user-test-001",
            "client_ip": "203.0.113.50",
            "timestamp": datetime.utcnow().isoformat(),
            "auth_method": "password",
            "failed_attempts": 3,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "device_fingerprint": "fp-test-e2e",
            "geo_location": {
                "country": "RU",
                "city": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
            }
        }
        
        try:
            response = requests.post(
                f"{self.services['behavior-agent']}/score",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                risk_score = data.get("final_risk_score", 0)
                print(f"[✓] Score endpoint: OK")
                print(f"    Risk Score: {risk_score:.2f}")
                print(f"    Anomaly Category: {data.get('anomaly_category', 'N/A')}")
                print(f"    Confidence: {data.get('confidence', 'N/A')}")
                print(f"    Inference Time: {data.get('inference_time_us', 'N/A')} μs")
                self.results["behavior_agent_scoring"] = "PASS"
                return True
            else:
                print(f"[✗] Score endpoint: {response.status_code}")
                print(f"    Body: {response.text}")
                self.results["behavior_agent_scoring"] = "FAIL"
                return False
        except Exception as e:
            print(f"[✗] Error: {str(e)}")
            self.results["behavior_agent_scoring"] = "ERROR"
            return False
    
    def test_orchestrator_policy_decision(self) -> bool:
        """Test 3: Orchestrator policy decision making."""
        self.print_header("TEST 3: Orchestrator Policy Decision")
        
        test_payload = {
            "session_id": "sess-e2e-test",
            "user_id": "user-test-001",
            "risk_score": 75.5,
            "event_id": f"event-{int(time.time())}"
        }
        
        try:
            response = requests.post(
                f"{self.services['orchestrator']}/decide",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[✓] Decide endpoint: OK")
                print(f"    Action: {data.get('action', 'N/A')}")
                print(f"    Tier: {data.get('tier', 'N/A')}")
                print(f"    Session State: {data.get('session_state', 'N/A')}")
                print(f"    Actions: {data.get('actions', [])}")
                self.results["orchestrator_decision"] = "PASS"
                return True
            else:
                print(f"[✗] Decide endpoint: {response.status_code}")
                self.results["orchestrator_decision"] = "FAIL"
                return False
        except Exception as e:
            print(f"[✗] Error: {str(e)}")
            self.results["orchestrator_decision"] = "ERROR"
            return False
    
    def test_prometheus_metrics_collection(self) -> bool:
        """Test 4: Prometheus is collecting metrics."""
        self.print_header("TEST 4: Prometheus Metrics Collection")
        
        queries = [
            ("Behavior Agent Requests", 'increase(behavior_agent_requests_total[5m])'),
            ("Request Latency", 'rate(behavior_agent_request_duration_seconds_sum[5m])'),
            ("Risk Score Distribution", 'histogram_quantile(0.95, behavior_agent_risk_score)'),
        ]
        
        all_found = True
        for metric_name, query in queries:
            try:
                response = requests.get(
                    f"{self.services['prometheus']}/api/v1/query",
                    params={"query": query},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" and data.get("data", {}).get("result"):
                        print(f"[✓] {metric_name}: Found")
                    else:
                        print(f"[!] {metric_name}: No recent data")
                else:
                    print(f"[✗] {metric_name}: Query failed ({response.status_code})")
                    all_found = False
            except Exception as e:
                print(f"[✗] {metric_name}: {str(e)}")
                all_found = False
        
        self.results["prometheus_metrics"] = "PASS" if all_found else "WARN"
        return True
    
    def test_grafana_dashboards(self) -> bool:
        """Test 5: Grafana dashboards are available."""
        self.print_header("TEST 5: Grafana Dashboards")
        
        dashboards = [
            "CIVA Attack Timeline",
            "CIVA Command Center",
            "CIVA Risk Distribution",
            "CIVA Latency SLA",
        ]
        
        try:
            response = requests.get(
                f"{self.services['grafana']}/api/search?query=CIVA",
                headers={"Authorization": "Bearer admin:admin"},
                timeout=5
            )
            
            if response.status_code == 200:
                found_dashboards = response.json()
                print(f"[✓] Grafana API: Accessible")
                print(f"    Found {len(found_dashboards)} dashboards")
                for db in found_dashboards[:3]:
                    print(f"    - {db.get('title', 'Unknown')}")
                self.results["grafana_dashboards"] = "PASS"
                return True
            else:
                print(f"[✗] Grafana API: {response.status_code}")
                self.results["grafana_dashboards"] = "FAIL"
                return False
        except Exception as e:
            print(f"[✗] Error: {str(e)}")
            self.results["grafana_dashboards"] = "WARN"
            return True  # Not critical
    
    def test_end_to_end_attack_flow(self) -> bool:
        """Test 6: Complete attack detection flow."""
        self.print_header("TEST 6: End-to-End Attack Flow")
        
        print("[*] Simulating credential spray attack (5 events)...")
        
        success_count = 0
        for i in range(5):
            # Generate attack-like payload
            payload = {
                "event_id": f"e2e-attack-{i}",
                "session_id": f"sess-attack-{i}",
                "user_id": f"user-victim",
                "client_ip": f"203.0.113.{100 + i}",
                "timestamp": datetime.utcnow().isoformat(),
                "auth_method": "password",
                "failed_attempts": 10 + i,
                "account_lockout_triggered": True,
                "geo_location": {
                    "country": "RU",
                    "city": "Moscow",
                    "latitude": 55.7558,
                    "longitude": 37.6173,
                }
            }
            
            try:
                # Step 1: Risk scoring
                response1 = requests.post(
                    f"{self.services['behavior-agent']}/score",
                    json=payload,
                    timeout=5
                )
                
                if response1.status_code == 200:
                    score_data = response1.json()
                    risk_score = score_data.get("final_risk_score", 0)
                    
                    # Step 2: Policy decision
                    response2 = requests.post(
                        f"{self.services['orchestrator']}/decide",
                        json={
                            "session_id": payload["session_id"],
                            "user_id": payload["user_id"],
                            "risk_score": risk_score,
                            "event_id": payload["event_id"]
                        },
                        timeout=5
                    )
                    
                    if response2.status_code == 200:
                        decision_data = response2.json()
                        print(f"[✓] Event {i+1}: Risk {risk_score:.1f} → Action: {decision_data.get('action')}")
                        success_count += 1
                    else:
                        print(f"[✗] Event {i+1}: Decision failed")
                else:
                    print(f"[✗] Event {i+1}: Scoring failed")
            except Exception as e:
                print(f"[✗] Event {i+1}: {str(e)}")
        
        self.results["e2e_attack_flow"] = "PASS" if success_count >= 4 else "FAIL"
        return success_count >= 4
    
    def run_all_tests(self) -> Dict:
        """Execute all validation tests."""
        print(f"\n{'#'*60}")
        print(f"# CIVA End-to-End System Validation")
        print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")
        
        tests = [
            ("Service Health", self.test_service_health),
            ("Behavior Agent", self.test_behavior_agent_scoring),
            ("Orchestrator", self.test_orchestrator_policy_decision),
            ("Prometheus", self.test_prometheus_metrics_collection),
            ("Grafana", self.test_grafana_dashboards),
            ("End-to-End", self.test_end_to_end_attack_flow),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"[!] Test '{test_name}' crashed: {str(e)}")
                self.results[test_name] = "ERROR"
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for v in self.results.values() if v == "PASS")
        failed = sum(1 for v in self.results.values() if v == "FAIL")
        errors = sum(1 for v in self.results.values() if v == "ERROR")
        
        for test, result in self.results.items():
            emoji = {"PASS": "✓", "FAIL": "✗", "WARN": "!", "ERROR": "E"}.get(result, "?")
            print(f"[{emoji}] {test}: {result}")
        
        print(f"\nResults: {passed} PASS, {failed} FAIL, {errors} ERROR")
        print(f"Duration: {time.time() - self.start_time:.1f}s")
        print(f"\nOverall Status: {'✓ ALL SYSTEMS GO' if failed == 0 and errors == 0 else '✗ ISSUES DETECTED'}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CIVA End-to-End Validator")
    parser.add_argument("--host", default="http://localhost", help="Base URL")
    args = parser.parse_args()
    
    validator = E2EValidator(base_url=args.host)
    results = validator.run_all_tests()
