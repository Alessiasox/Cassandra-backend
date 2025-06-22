#!/usr/bin/env python3
"""
Simple script to display performance metrics from the test report.
"""

import json
import os
from datetime import datetime

def show_performance_report():
    """Display the performance report in a readable format."""
    report_path = "performance_report.json"
    
    if not os.path.exists(report_path):
        print("Performance report not found. Run 'make test' first.")
        return
    
    with open(report_path, 'r') as f:
        data = json.load(f)
    
    print("CASSANDRA BACKEND PERFORMANCE REPORT")
    print("=" * 50)
    
    # Test run info
    test_run = datetime.fromisoformat(data["test_run"])
    print(f"Test Run: {test_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Individual test results
    for test_name, test_data in data["tests"].items():
        print(f"{test_name.upper()}")
        print("-" * 30)
        
        metrics = test_data["metrics"]
        timestamp = datetime.fromisoformat(test_data["timestamp"])
        print(f"   Time: {timestamp.strftime('%H:%M:%S')}")
        
        if "api_latency" in metrics:
            print(f"   API Latency: {metrics['api_latency']:.4f}s")
        
        if "download_latency" in metrics:
            print(f"   Download Latency: {metrics['download_latency']:.4f}s")
        
        if "download_latencies" in metrics:
            for res, latency in metrics["download_latencies"].items():
                print(f"   {res} Download: {latency:.4f}s")
        
        if "total_time" in metrics:
            print(f"   Total Time: {metrics['total_time']:.4f}s")
        
        if "frames_found" in metrics:
            print(f"   Frames Found: {metrics['frames_found']}")
        
        if "date_tested" in metrics:
            print(f"   Date Tested: {metrics['date_tested']}")
        
        if "filename" in metrics:
            print(f"   File: {metrics['filename']}")
        
        if "resolution" in metrics:
            print(f"   Resolution: {metrics['resolution']}")
        
        print()
    
    # Summary
    print("SUMMARY")
    print("-" * 30)
    total_tests = len(data["tests"])
    total_time = sum(test["metrics"].get("total_time", 0) for test in data["tests"].values())
    avg_api_latency = sum(test["metrics"].get("api_latency", 0) for test in data["tests"].values()) / total_tests
    
    print(f"   Tests Run: {total_tests}")
    print(f"   Total Time: {total_time:.4f}s")
    print(f"   Average API Latency: {avg_api_latency:.4f}s")

if __name__ == "__main__":
    show_performance_report() 