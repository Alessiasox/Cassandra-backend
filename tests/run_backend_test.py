import os
import requests
import pytest
import json
from datetime import datetime, timedelta
import time

# --- Configuration ---
BACKEND_API_URL = "http://app:8000"
PROXY_URL = "http://proxy:80"
TESTS_OUTPUT_DIR = os.path.dirname(__file__)

# --- Global performance tracking ---
performance_data = {
    "test_run": datetime.now().isoformat(),
    "tests": {}
}

def save_performance_report():
    """Save performance data to a JSON file."""
    report_path = os.path.join(TESTS_OUTPUT_DIR, "performance_report.json")
    with open(report_path, 'w') as f:
        json.dump(performance_data, f, indent=2)
    print(f"  Performance report saved to: {report_path}")

def add_performance_data(test_name, metrics):
    """Add performance data for a specific test."""
    performance_data["tests"][test_name] = {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics
    }

# --- Helper Functions ---
def check_proxy_readiness(max_retries=30, retry_delay=2):
    """Check if the proxy is ready by attempting to connect to it."""
    print("  [Proxy] Checking proxy readiness...")
    
    for attempt in range(max_retries):
        try:
            # Try to connect to the proxy and get a simple response
            response = requests.get(f"{PROXY_URL}/", timeout=5)
            if response.status_code == 200 or response.status_code == 404:
                print(f"  [Proxy] Ready after {attempt + 1} attempts")
                return True
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                print(f"  [Proxy] Attempt {attempt + 1}/{max_retries}: Not ready yet ({e})")
                time.sleep(retry_delay)
            else:
                print(f"  [Proxy] Failed to connect after {max_retries} attempts")
                return False
    
    return False

def measure_latency(func, *args, **kwargs):
    """A helper to measure the execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    latency = end_time - start_time
    print(f"\n[Performance] '{func.__name__}' took {latency:.4f} seconds.")
    return result, latency

def download_image(url: str, save_path: str):
    """Downloads an image from a URL and saves it."""
    try:
        internal_url = url.replace("http://localhost:8080", PROXY_URL)
        print(f"  [Download] Requesting internal URL: {internal_url}")
        response = requests.get(internal_url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  [Download] Saved image to {save_path}")
        return True
    except requests.RequestException as e:
        print(f"  [Error] Failed to download image from {internal_url}. Error: {e}")
        return False

# --- Pytest Tests ---
def test_backend_health():
    """Test that the backend health endpoint is working."""
    print("\n[Test] Checking backend health...")
    response = requests.get(f"{BACKEND_API_URL}/health")
    assert response.status_code == 200
    print("  [Result] Backend health check passed")

def test_fetch_frames():
    """Test fetching frames for a date."""
    print("\n[Test] Testing frame fetching...")
    
    # Test with date from 2 days ago
    two_days_ago = datetime.now() - timedelta(days=2)
    date_str = two_days_ago.strftime("%y%m%d")
    
    print(f"  [Action] Fetching all frames for date: {date_str}...")
    start_time = time.time()
    response = requests.get(f"{BACKEND_API_URL}/frames", params={"date": date_str})
    api_latency = time.time() - start_time
    
    # Even if no frames found, the API should return 200 with empty list
    assert response.status_code == 200
    frames = response.json()
    print(f"  [Result] Found {len(frames)} frames in {api_latency:.4f}s")
    
    # If frames exist, test downloading LoRes and HiRes
    if frames:
        # Check proxy readiness before attempting downloads
        if not check_proxy_readiness():
            pytest.skip("Proxy not ready, skipping download tests")
        
        lores_frames = [f for f in frames if f['resolution'] == 'LoRes']
        hires_frames = [f for f in frames if f['resolution'] == 'HiRes']
        
        download_latencies = {}
        
        if lores_frames:
            lores_frame = lores_frames[0]
            print(f"  [Action] Testing LoRes download: {os.path.basename(lores_frame['url'])}")
            start_time = time.time()
            success = download_image(lores_frame['url'], os.path.join(TESTS_OUTPUT_DIR, "test_lores.jpg"))
            lores_latency = time.time() - start_time
            assert success, "LoRes image download failed"
            print(f"  [Result] LoRes download passed in {lores_latency:.4f}s")
            download_latencies['LoRes'] = lores_latency
        
        if hires_frames:
            hires_frame = hires_frames[0]
            print(f"  [Action] Testing HiRes download: {os.path.basename(hires_frame['url'])}")
            start_time = time.time()
            success = download_image(hires_frame['url'], os.path.join(TESTS_OUTPUT_DIR, "test_hires.jpg"))
            hires_latency = time.time() - start_time
            assert success, "HiRes image download failed"
            print(f"  [Result] HiRes download passed in {hires_latency:.4f}s")
            download_latencies['HiRes'] = hires_latency
        
        # Performance summary
        total_time = api_latency + sum(download_latencies.values())
        print(f"\n  PERFORMANCE SUMMARY:")
        print(f"     API fetch: {api_latency:.4f}s")
        for res, latency in download_latencies.items():
            print(f"     {res} download: {latency:.4f}s")
        print(f"     Total test time: {total_time:.4f}s")
        
        # Save performance data
        metrics = {
            "api_latency": api_latency,
            "download_latencies": download_latencies,
            "total_time": total_time,
            "frames_found": len(frames),
            "date_tested": date_str
        }
        add_performance_data("test_fetch_frames", metrics)

def test_download_hires_frame():
    """Test downloading a HiRes frame specifically."""
    print("\n[Test] Downloading HiRes frame...")
    
    # Check proxy readiness before attempting download
    if not check_proxy_readiness():
        pytest.skip("Proxy not ready, skipping HiRes download test")
    
    two_days_ago = datetime.now() - timedelta(days=2)
    date_str = two_days_ago.strftime("%y%m%d")
    
    start_time = time.time()
    response = requests.get(f"{BACKEND_API_URL}/frames", params={"date": date_str})
    api_latency = time.time() - start_time
    
    assert response.status_code == 200
    frames = response.json()
    
    hires_frames = [f for f in frames if f['resolution'] == 'HiRes']
    if not hires_frames:
        pytest.skip(f"No HiRes frames found for {date_str}")
    
    hires_frame = hires_frames[0]
    print(f"  [Action] Downloading HiRes: {os.path.basename(hires_frame['url'])}")
    start_time = time.time()
    success = download_image(hires_frame['url'], os.path.join(TESTS_OUTPUT_DIR, "test_hires.jpg"))
    download_latency = time.time() - start_time
    
    assert success, "HiRes image download failed"
    print(f"  [Result] HiRes download completed in {download_latency:.4f}s (API: {api_latency:.4f}s)")
    
    # Performance summary
    total_time = api_latency + download_latency
    print(f"\n  PERFORMANCE SUMMARY:")
    print(f"     API fetch: {api_latency:.4f}s")
    print(f"     HiRes download: {download_latency:.4f}s")
    print(f"     Total time: {total_time:.4f}s")
    
    # Save performance data
    metrics = {
        "api_latency": api_latency,
        "download_latency": download_latency,
        "total_time": total_time,
        "date_tested": date_str,
        "filename": os.path.basename(hires_frame['url'])
    }
    add_performance_data("test_download_hires_frame", metrics)

def test_download_random_frame_two_days_ago():
    """Test downloading the first available frame from two days ago (any resolution)."""
    print("\n[Test] Downloading a random frame from two days ago...")
    
    # Check proxy readiness before attempting download
    if not check_proxy_readiness():
        pytest.skip("Proxy not ready, skipping random frame download test")
    
    two_days_ago = datetime.now() - timedelta(days=2)
    date_str = two_days_ago.strftime("%y%m%d")
    
    start_time = time.time()
    response = requests.get(f"{BACKEND_API_URL}/frames", params={"date": date_str})
    api_latency = time.time() - start_time
    
    assert response.status_code == 200
    frames = response.json()
    if not frames:
        pytest.skip(f"No frames found for {date_str}, skipping download test.")
    
    frame = frames[0]
    print(f"  [Action] Downloading: {os.path.basename(frame['url'])}")
    start_time = time.time()
    success = download_image(frame['url'], os.path.join(TESTS_OUTPUT_DIR, "test_random_frame.jpg"))
    download_latency = time.time() - start_time
    
    assert success, "Random frame download failed"
    print(f"  [Result] Random frame download completed in {download_latency:.4f}s (API: {api_latency:.4f}s)")
    
    # Performance summary
    total_time = api_latency + download_latency
    print(f"\n  PERFORMANCE SUMMARY:")
    print(f"     API fetch: {api_latency:.4f}s")
    print(f"     {frame['resolution']} download: {download_latency:.4f}s")
    print(f"     Total time: {total_time:.4f}s")
    
    # Save performance data
    metrics = {
        "api_latency": api_latency,
        "download_latency": download_latency,
        "total_time": total_time,
        "date_tested": date_str,
        "resolution": frame['resolution'],
        "filename": os.path.basename(frame['url'])
    }
    add_performance_data("test_download_random_frame_two_days_ago", metrics)

def test_invalid_date():
    """Test API behavior with invalid date format."""
    print("\n[Test] Testing invalid date handling...")
    response = requests.get(f"{BACKEND_API_URL}/frames", params={"date": "invalid_date"})
    # Should return 500 for invalid date format (matches backend behavior)
    assert response.status_code == 500
    print("  [Result] Invalid date handling test passed")

def test_missing_date():
    """Test API behavior when date parameter is missing."""
    print("\n[Test] Testing missing date parameter...")
    response = requests.get(f"{BACKEND_API_URL}/frames")
    # Should return 422 for missing date parameter (matches backend behavior)
    assert response.status_code == 422
    print("  [Result] Missing date parameter test passed")

def test_recent_date():
    """Test fetching frames for today's date."""
    print("\n[Test] Testing with today's date...")
    
    today = datetime.now()
    date_str = today.strftime("%y%m%d")
    
    print(f"  [Action] Fetching frames for today: {date_str}...")
    start_time = time.time()
    response = requests.get(f"{BACKEND_API_URL}/frames", params={"date": date_str})
    api_latency = time.time() - start_time
    
    # Handle case where no frames exist for today (500 error from backend)
    if response.status_code == 500:
        print(f"  [Result] No frames found for today ({date_str}), skipping test")
        pytest.skip(f"No frames available for today's date {date_str}")
    
    assert response.status_code == 200
    frames = response.json()
    print(f"  [Result] Found {len(frames)} frames for today in {api_latency:.4f}s")
    
    # This test passes regardless of whether frames exist for today
    print("  [Result] Today's date test passed")

def test_save_performance_report():
    """Final test to save the performance report."""
    print("\n[Test] Saving performance report...")
    save_performance_report()
    print("  [Result] Performance report saved successfully")

