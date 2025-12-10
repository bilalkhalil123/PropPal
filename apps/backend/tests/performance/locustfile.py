"""
Load testing scenarios for PropPal backend.

Run with: locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""
from locust import HttpUser, task, between


class PropertySearchUser(HttpUser):
    """Simulate users searching for properties"""
    wait_time = between(1, 3)
    
    @task(3)
    def search_properties(self):
        """Simulate property search"""
        self.client.post("/api/chat/message", json={
            "message": "Find apartments in Islamabad",
            "clerk_id": f"user_{self.environment.runner.user_count}",
            "session_id": "test_session"
        })
    
    @task(1)
    def get_property_details(self):
        """Simulate getting property details"""
        self.client.get("/api/properties/507f1f77bcf86cd799439011")
    
    @task(1)
    def list_sessions(self):
        """Simulate listing chat sessions"""
        self.client.get("/api/chat/sessions?user_id=test_user")
    
    @task(2)
    def search_builders(self):
        """Simulate builder search"""
        self.client.post("/api/chat/message", json={
            "message": "Find plumbing services in Lahore",
            "clerk_id": f"user_{self.environment.runner.user_count}",
            "session_id": "test_session"
        })

