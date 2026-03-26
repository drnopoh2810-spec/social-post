#!/usr/bin/env python3
"""
اختبار سريع للإصلاحات الجديدة في توليد الصور
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_image_validation():
    """Test image validation in upload_to_cloudinary"""
    from services.image_service import upload_to_cloudinary
    import io
    from PIL import Image
    
    print("🧪 Testing image validation...")
    
    # Test 1: Empty bytes
    try:
        upload_to_cloudinary(b"", "test", "test", "test")
        print("❌ Should have rejected empty bytes")
    except ValueError as e:
        print(f"✅ Correctly rejected empty bytes: {e}")
    
    # Test 2: Too small bytes
    try:
        upload_to_cloudinary(b"x" * 50, "test", "test", "test")
        print("❌ Should have rejected small bytes")
    except ValueError as e:
        print(f"✅ Correctly rejected small bytes: {e}")
    
    # Test 3: Invalid image data
    try:
        upload_to_cloudinary(b"not an image" * 100, "test", "test", "test")
        print("❌ Should have rejected invalid image")
    except ValueError as e:
        print(f"✅ Correctly rejected invalid image: {e}")
    
    # Test 4: Valid image (should pass validation, fail on upload)
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    valid_bytes = buf.getvalue()
    
    try:
        upload_to_cloudinary(valid_bytes, "test", "test", "test")
        print("❌ Should have failed on upload (bad credentials)")
    except Exception as e:
        if "Invalid image data" in str(e):
            print(f"❌ Should have passed validation: {e}")
        else:
            print(f"✅ Passed validation, failed on upload (expected): {type(e).__name__}")


def test_overlay_validation():
    """Test image validation in overlay service"""
    from services.overlay_service import apply_text_overlay
    import io
    from PIL import Image
    
    print("\n🧪 Testing overlay validation...")
    
    # Test 1: Empty bytes
    result = apply_text_overlay(b"", "test text")
    if result == b"":
        print("✅ Correctly returned empty bytes for empty input")
    else:
        print("❌ Should have returned empty bytes")
    
    # Test 2: Invalid image
    result = apply_text_overlay(b"not an image" * 100, "test text")
    if result == b"not an image" * 100:
        print("✅ Correctly returned original bytes for invalid image")
    else:
        print("❌ Should have returned original bytes")
    
    # Test 3: Valid image
    img = Image.new("RGB", (1080, 1350), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    valid_bytes = buf.getvalue()
    
    result = apply_text_overlay(valid_bytes, "اختبار النص العربي")
    if result and len(result) > len(valid_bytes) * 0.8:
        print(f"✅ Overlay processed valid image ({len(result)} bytes)")
    else:
        print(f"❌ Overlay failed on valid image")


def test_gemini_models():
    """Test updated Gemini models list"""
    from services.image_service import GEMINI_IMAGE_MODELS
    
    print("\n🧪 Testing Gemini models list...")
    
    # Check for stable models
    stable_models = ["gemini-1.5-flash", "gemini-1.5-pro", "imagen-3.0-generate-001"]
    for model in stable_models:
        if model in GEMINI_IMAGE_MODELS:
            print(f"✅ Found stable model: {model}")
        else:
            print(f"❌ Missing stable model: {model}")
    
    # Check for removed experimental models
    experimental = ["imagen-4.0-generate-001", "gemini-2.0-flash-exp"]
    for model in experimental:
        if model not in GEMINI_IMAGE_MODELS:
            print(f"✅ Removed experimental model: {model}")
        else:
            print(f"⚠️  Still has experimental model: {model}")


def test_airforce_pythonanywhere_check():
    """Test PythonAnywhere detection for api.airforce"""
    import os
    
    print("\n🧪 Testing PythonAnywhere detection...")
    
    # Simulate PythonAnywhere environment
    os.environ["PYTHONANYWHERE_DOMAIN"] = "test.pythonanywhere.com"
    
    from services.image_service import _try_airforce
    result = _try_airforce("test prompt", 1024, 1024)
    
    if result is None:
        print("✅ Correctly skipped api.airforce on PythonAnywhere")
    else:
        print("❌ Should have skipped api.airforce on PythonAnywhere")
    
    # Clean up
    del os.environ["PYTHONANYWHERE_DOMAIN"]


def main():
    print("=" * 60)
    print("🔧 اختبار الإصلاحات الجديدة لتوليد الصور")
    print("=" * 60)
    
    try:
        test_image_validation()
        test_overlay_validation()
        test_gemini_models()
        test_airforce_pythonanywhere_check()
        
        print("\n" + "=" * 60)
        print("✅ جميع الاختبارات اكتملت!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
