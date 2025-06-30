#!/usr/bin/env python3
"""
Integration test script for AI Invoice Processing Agent
"""
import asyncio
import sys
import time
import requests
import json
from pathlib import Path
from PIL import Image
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings


class IntegrationTester:
    """Integration tester for the complete system"""
    
    def __init__(self):
        self.api_base_url = f"http://{settings.host}:{settings.port}"
        self.dashboard_url = f"http://{settings.host}:{settings.dashboard_port}"
        self.test_results = []
        self.temp_dir = None
    
    def setup(self):
        """Setup test environment"""
        print("🔧 Setting up integration test environment...")
        
        # Create temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        print(f"📁 Created temporary directory: {self.temp_dir}")
        
        # Ensure required directories exist
        settings.incoming_path.mkdir(parents=True, exist_ok=True)
        settings.generated_path.mkdir(parents=True, exist_ok=True)
        settings.log_path.mkdir(parents=True, exist_ok=True)
        
        print("✅ Test environment setup complete")
    
    def cleanup(self):
        """Cleanup test environment"""
        print("🧹 Cleaning up test environment...")
        
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        print("✅ Cleanup complete")
    
    def create_test_invoice_image(self, filename: str) -> Path:
        """Create a test invoice image"""
        # Create a simple test image with some text-like patterns
        img = Image.new('RGB', (800, 600), color='white')
        
        # Add some colored rectangles to simulate invoice content
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Header area
        draw.rectangle([50, 50, 750, 100], fill='lightblue')
        
        # Invoice details area
        draw.rectangle([50, 120, 400, 300], fill='lightgray')
        
        # Line items area
        draw.rectangle([50, 320, 750, 500], fill='lightyellow')
        
        # Total area
        draw.rectangle([500, 520, 750, 570], fill='lightgreen')
        
        # Save image
        image_path = self.temp_dir / filename
        img.save(image_path, 'JPEG')
        
        return image_path
    
    def test_api_health(self) -> bool:
        """Test API health endpoint"""
        print("🏥 Testing API health...")
        
        try:
            response = requests.get(f"{self.api_base_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is healthy - Status: {data.get('status')}")
                return True
            else:
                print(f"❌ API health check failed - Status: {response.status_code}")
                return False
        
        except requests.exceptions.RequestException as e:
            print(f"❌ API health check failed - Error: {str(e)}")
            return False
    
    def test_file_upload(self) -> bool:
        """Test file upload functionality"""
        print("📤 Testing file upload...")
        
        try:
            # Create test image
            test_image = self.create_test_invoice_image("test_upload.jpg")
            
            # Upload file
            with open(test_image, 'rb') as f:
                files = {"file": ("test_upload.jpg", f, "image/jpeg")}
                response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ File upload successful - Filename: {data['data']['filename']}")
                return True
            else:
                print(f"❌ File upload failed - Status: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ File upload test failed - Error: {str(e)}")
            return False
    
    def test_manual_processing(self) -> bool:
        """Test manual processing trigger"""
        print("⚙️ Testing manual processing...")
        
        try:
            # Create test image in incoming folder
            test_image = self.create_test_invoice_image("test_manual.jpg")
            target_path = settings.incoming_path / "test_manual.jpg"
            shutil.copy2(test_image, target_path)
            
            # Trigger processing
            request_data = {"force_reprocess": True}
            response = requests.post(f"{self.api_base_url}/process", json=request_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Manual processing triggered - Message: {data['message']}")
                
                # Wait for processing to complete
                print("⏳ Waiting for processing to complete...")
                time.sleep(10)
                
                return True
            else:
                print(f"❌ Manual processing failed - Status: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Manual processing test failed - Error: {str(e)}")
            return False
    
    def test_statistics_endpoint(self) -> bool:
        """Test statistics endpoint"""
        print("📊 Testing statistics endpoint...")
        
        try:
            response = requests.get(f"{self.api_base_url}/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Statistics retrieved - Total processed: {data.get('total_processed', 0)}")
                print(f"   Successful: {data.get('successful', 0)}, Failed: {data.get('failed', 0)}")
                return True
            else:
                print(f"❌ Statistics test failed - Status: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Statistics test failed - Error: {str(e)}")
            return False
    
    def test_results_endpoint(self) -> bool:
        """Test results endpoint"""
        print("📋 Testing results endpoint...")
        
        try:
            response = requests.get(f"{self.api_base_url}/results", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Results retrieved - Count: {len(data)}")
                
                if data:
                    latest_result = data[0]
                    print(f"   Latest result: {latest_result.get('original_filename')} - {latest_result.get('status')}")
                
                return True
            else:
                print(f"❌ Results test failed - Status: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Results test failed - Error: {str(e)}")
            return False
    
    def test_dashboard_accessibility(self) -> bool:
        """Test dashboard accessibility"""
        print("🖥️ Testing dashboard accessibility...")
        
        try:
            response = requests.get(self.dashboard_url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Dashboard is accessible")
                return True
            else:
                print(f"❌ Dashboard accessibility test failed - Status: {response.status_code}")
                return False
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Dashboard accessibility test failed - Error: {str(e)}")
            print("ℹ️ Note: Dashboard might not be running. Start it with: streamlit run dashboard/app.py")
            return False
    
    def test_file_processing_workflow(self) -> bool:
        """Test complete file processing workflow"""
        print("🔄 Testing complete file processing workflow...")
        
        try:
            # Create multiple test images
            test_images = []
            for i in range(3):
                image_path = self.create_test_invoice_image(f"workflow_test_{i}.jpg")
                target_path = settings.incoming_path / f"workflow_test_{i}.jpg"
                shutil.copy2(image_path, target_path)
                test_images.append(target_path)
            
            print(f"📁 Created {len(test_images)} test files in incoming folder")
            
            # Wait for automatic processing
            print("⏳ Waiting for automatic processing...")
            time.sleep(15)
            
            # Check if files were processed
            generated_files = list(settings.generated_path.glob("workflow_test_*.json"))
            moved_images = list(settings.generated_path.glob("workflow_test_*.jpg"))
            
            print(f"📄 Generated JSON files: {len(generated_files)}")
            print(f"📷 Moved image files: {len(moved_images)}")
            
            # Check if original files were removed from incoming
            remaining_files = list(settings.incoming_path.glob("workflow_test_*.jpg"))
            print(f"📁 Remaining files in incoming: {len(remaining_files)}")
            
            if generated_files and moved_images and len(remaining_files) == 0:
                print("✅ Complete workflow test successful")
                
                # Check content of a generated JSON file
                if generated_files:
                    with open(generated_files[0], 'r') as f:
                        json_content = json.load(f)
                    print(f"📄 Sample JSON content keys: {list(json_content.keys())}")
                
                return True
            else:
                print("❌ Complete workflow test failed - Files not processed correctly")
                return False
        
        except Exception as e:
            print(f"❌ Complete workflow test failed - Error: {str(e)}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid files"""
        print("🚫 Testing error handling...")
        
        try:
            # Create invalid file (text file with image extension)
            invalid_file = self.temp_dir / "invalid.jpg"
            with open(invalid_file, 'w') as f:
                f.write("This is not an image file")
            
            # Try to upload invalid file
            with open(invalid_file, 'rb') as f:
                files = {"file": ("invalid.jpg", f, "image/jpeg")}
                response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=30)
            
            # Should still accept upload (validation happens during processing)
            if response.status_code == 200:
                print("✅ Invalid file upload handled gracefully")
                
                # Wait and check if error was logged properly
                time.sleep(5)
                
                # Check statistics for failed processing
                stats_response = requests.get(f"{self.api_base_url}/stats", timeout=10)
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"📊 Failed processing count: {stats.get('failed', 0)}")
                
                return True
            else:
                print(f"❌ Error handling test failed - Status: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Error handling test failed - Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting AI Invoice Processing Agent Integration Tests")
        print("=" * 60)
        
        self.setup()
        
        tests = [
            ("API Health Check", self.test_api_health),
            ("File Upload", self.test_file_upload),
            ("Manual Processing", self.test_manual_processing),
            ("Statistics Endpoint", self.test_statistics_endpoint),
            ("Results Endpoint", self.test_results_endpoint),
            ("Dashboard Accessibility", self.test_dashboard_accessibility),
            ("Complete Workflow", self.test_file_processing_workflow),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                if result:
                    passed += 1
                    self.test_results.append((test_name, "PASSED"))
                else:
                    self.test_results.append((test_name, "FAILED"))
            except Exception as e:
                print(f"❌ Test {test_name} crashed - Error: {str(e)}")
                self.test_results.append((test_name, "CRASHED"))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        for test_name, status in self.test_results:
            status_icon = "✅" if status == "PASSED" else "❌"
            print(f"{status_icon} {test_name}: {status}")
        
        print(f"\n📈 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System is working correctly.")
        else:
            print("⚠️ Some tests failed. Please check the logs and fix issues.")
        
        self.cleanup()
        
        return passed == total


def main():
    """Main function"""
    tester = IntegrationTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

