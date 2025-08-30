
import redis
import string
import random
from typing import Optional

# Redis Configuration
redis_client = redis.Redis(
    host='redis-15440.c93.us-east-1-3.ec2.redns.redis-cloud.com',
    port=15440,
    decode_responses=True,
    username="default",
    password="Af1Y9RyLA2mSlpuEfoR99YfvBx0YmRvS"
)

def load_admin_ids():
    """Load admin user IDs from admin.txt"""
    try:
        with open('admin.txt', 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

def generate_token():
    """Generate a 10-character alphanumeric token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def is_admin(user_id):
    """Check if user is admin"""
    admin_ids = load_admin_ids()
    return int(user_id) in admin_ids

async def get_user_token(user_id):
    """Get user's token"""
    return redis_client.get(f"user_token:{user_id}")

async def set_user_token(user_id, token):
    """Set user's token"""
    redis_client.set(f"user_token:{user_id}", token)
    redis_client.set(f"token_user:{token}", user_id)

async def revoke_user_token(user_id):
    """Revoke user's token"""
    old_token = redis_client.get(f"user_token:{user_id}")
    if old_token:
        redis_client.delete(f"token_user:{old_token}")
    redis_client.delete(f"user_token:{user_id}")

def get_user_by_token(token):
    """Get user ID by token"""
    user_id = redis_client.get(f"token_user:{token}")
    return int(user_id) if user_id else None

async def get_user_request_count(user_id):
    """Get user's daily request count"""
    return int(redis_client.get(f"user_requests:{user_id}") or 0)

async def set_user_request_count(user_id, count):
    """Set user's daily request count"""
    redis_client.setex(f"user_requests:{user_id}", 86400, count)  # 24 hours TTL

async def increment_user_requests(user_id):
    """Increment user's daily request count"""
    key = f"user_requests:{user_id}"
    current = int(redis_client.get(key) or 0)
    redis_client.setex(key, 86400, current + 1)
    return current + 1
