#!/usr/bin/env python3
"""
Simple test script for S3 URL refresh functionality.
Run with: python utils/test_s3_refresh.py
"""

import sys
import os

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.s3_url_refresh import S3UrlRefresher, S3_URL_PATTERN

def test_s3_url_detection():
    """Test S3 URL pattern detection."""
    print("Testing S3 URL pattern detection...")
    
    # Test cases - both signed and unsigned S3 URLs
    test_urls = [
        # Signed URLs
        "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA...&X-Amz-Date=20231201T120000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=abc123",
        "https://another-bucket.s3.amazonaws.com/documents/report.pdf?X-Amz-Signature=def456&X-Amz-Expires=7200",
        # Unsigned URLs (like the user's example)
        "https://polysynergy-8865bb5f-1ce573d4-media.s3.amazonaws.com/HR/Stellar%2020240422%20Personeelsgids%20rev%207.docx",
        "https://my-bucket.s3.eu-west-1.amazonaws.com/images/photo.png",
        # Non-S3 URLs
        "https://example.com/not-s3-url.jpg",
    ]
    
    print(f"S3 URL Pattern: {S3_URL_PATTERN.pattern}")
    print()
    
    for i, url in enumerate(test_urls, 1):
        match = S3_URL_PATTERN.search(url)
        print(f"Test {i}: {'✓ MATCH' if match else '✗ NO MATCH'}")
        print(f"  URL: {url[:80]}{'...' if len(url) > 80 else ''}")
        if match:
            print(f"  Matched: {match.group(0)[:80]}{'...' if len(match.group(0)) > 80 else ''}")
        print()

def test_s3_info_extraction():
    """Test S3 bucket and key extraction."""
    print("Testing S3 info extraction...")
    
    refresher = S3UrlRefresher()
    
    test_cases = [
        {
            "url": "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.jpg?X-Amz-Signature=abc123",
            "expected_bucket": "my-bucket",
            "expected_key": "path/to/file.jpg"
        },
        {
            "url": "https://another-bucket.s3.amazonaws.com/documents/report.pdf?X-Amz-Signature=def456",
            "expected_bucket": "another-bucket", 
            "expected_key": "documents/report.pdf"
        },
        {
            "url": "https://polysynergy-8865bb5f-1ce573d4-media.s3.amazonaws.com/HR/Stellar%2020240422%20Personeelsgids%20rev%207.docx",
            "expected_bucket": "polysynergy-8865bb5f-1ce573d4-media",
            "expected_key": "HR/Stellar%2020240422%20Personeelsgids%20rev%207.docx"
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        info = refresher.extract_s3_info_from_url(case["url"])
        print(f"Test {i}:")
        print(f"  URL: {case['url'][:60]}...")
        if info:
            print(f"  ✓ Bucket: {info['bucket']} (expected: {case['expected_bucket']})")
            print(f"  ✓ Key: {info['key']} (expected: {case['expected_key']})")
            
            bucket_match = info['bucket'] == case['expected_bucket']
            key_match = info['key'] == case['expected_key']
            print(f"  Result: {'✓ SUCCESS' if bucket_match and key_match else '✗ FAILED'}")
        else:
            print(f"  ✗ No info extracted")
        print()

def test_text_processing():
    """Test text processing with S3 URLs."""
    print("Testing text processing...")
    
    sample_text = """
Here are your files:
1. https://my-bucket.s3.us-east-1.amazonaws.com/reports/report1.pdf?X-Amz-Signature=abc123
2. https://my-bucket.s3.us-east-1.amazonaws.com/images/chart.png?X-Amz-Signature=def456

You can also visit https://example.com/regular-url which is not an S3 URL.

Another S3 file: https://data-bucket.s3.amazonaws.com/data.csv?X-Amz-Signature=xyz789

And here's an unsigned S3 URL: https://polysynergy-8865bb5f-1ce573d4-media.s3.amazonaws.com/HR/Stellar%2020240422%20Personeelsgids%20rev%207.docx
"""
    
    refresher = S3UrlRefresher()
    
    # Find all S3 URLs
    matches = S3_URL_PATTERN.findall(sample_text)
    print(f"Found {len(matches)} S3 URLs in sample text:")
    for i, url in enumerate(matches, 1):
        print(f"  {i}. {url[:60]}...")
    print()
    
    # Test the refresh function (will not actually refresh due to no S3 credentials in test)
    print("Testing refresh_s3_urls_in_text function...")
    result = refresher.refresh_s3_urls_in_text(sample_text)
    print("✓ Function executed without errors")
    print(f"  Original text length: {len(sample_text)}")
    print(f"  Processed text length: {len(result)}")
    print()

if __name__ == "__main__":
    print("=== S3 URL Refresh Utility Test ===\n")
    
    test_s3_url_detection()
    print("-" * 50)
    test_s3_info_extraction()
    print("-" * 50)
    test_text_processing()
    
    print("=== Test Complete ===")
    print("\nNote: Actual URL refresh requires valid AWS credentials and S3 access.")
    print("This test only verifies URL detection and parsing logic.")