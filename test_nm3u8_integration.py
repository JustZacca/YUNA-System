#!/usr/bin/env python3
"""
Test script for N_m3u8DL-RE integration.
Tests the new downloader functionality.
"""

import os
import sys
import asyncio
import tempfile
import logging

# Add src to path
sys.path.insert(0, "src")

from yuna.providers.streamingcommunity.nm3u8_downloader import (
    Nm3u8Config, 
    Nm3u8DLREDownloader,
    create_downloader
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_binary_detection():
    """Test N_m3u8DL-RE binary detection."""
    print("🔍 Testing N_m3u8DL-RE binary detection...")
    
    config = Nm3u8Config()
    downloader = Nm3u8DLREDownloader("/tmp")
    
    if downloader.is_available():
        print("✅ N_m3u8DL-RE binary found and working")
        return True
    else:
        print("❌ N_m3u8DL-RE binary not found")
        print("💡 Run 'python install_nm3u8.py' to install it")
        return False


async def test_downloader_creation():
    """Test downloader creation with fallback."""
    print("\n🏭 Testing downloader creation...")
    
    # Test with N_m3u8DL-RE preference
    downloader1 = create_downloader("/tmp", prefer_nm3u8=True)
    print(f"✅ Created downloader (prefer N_m3u8DL-RE): {type(downloader1).__name__}")
    
    # Test with ffmpeg preference
    downloader2 = create_downloader("/tmp", prefer_nm3u8=False)
    print(f"✅ Created downloader (prefer ffmpeg): {type(downloader2).__name__}")
    
    return True


async def test_streamingcommunity_integration():
    """Test StreamingCommunity integration."""
    print("\n🎬 Testing StreamingCommunity integration...")
    
    try:
        from yuna.providers.streamingcommunity.client import StreamingCommunity, Nm3u8Config
        
        # Create config with N_m3u8DL-RE settings
        config = Nm3u8Config(
            thread_count=8,
            timeout=30,
            auto_select=True
        )
        
        # Initialize StreamingCommunity with N_m3u8DL-RE
        sc = StreamingCommunity(
            prefer_nm3u8=True,
            nm3u8_config=config
        )
        
        print("✅ StreamingCommunity initialized with N_m3u8DL-RE support")
        
        # Test search (should work)
        results = sc.search("test")
        print(f"✅ Search test successful (found {len(results)} results)")
        
        return True
        
    except Exception as e:
        print(f"❌ StreamingCommunity integration test failed: {e}")
        return False


async def test_configuration():
    """Test configuration loading from environment."""
    print("\n⚙️ Testing configuration...")
    
    # Test default config
    config1 = Nm3u8Config()
    print(f"✅ Default config - threads: {config1.thread_count}, timeout: {config1.timeout}")
    
    # Test custom config
    config2 = Nm3u8Config(
        thread_count=32,
        timeout=60,
        max_speed="10M",
        headers={"Custom": "Header"}
    )
    print(f"✅ Custom config - threads: {config2.thread_count}, speed_limit: {config2.max_speed}")
    
    return True


async def main():
    """Run all tests."""
    print("🧪 YUNA-System N_m3u8DL-RE Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Binary Detection", test_binary_detection),
        ("Downloader Creation", test_downloader_creation),
        ("Configuration", test_configuration),
        ("StreamingCommunity Integration", test_streamingcommunity_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! N_m3u8DL-RE integration is working.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))