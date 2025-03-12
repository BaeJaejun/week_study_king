from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# 1. MongoDB 연결
client = MongoClient("mongodb://localhost:27017/")
db = client["week_study_king"]
users_collection = db["users"]

# 2. 초기화 (기존 데이터 삭제: 테스트용)
users_collection.delete_many({})  # ❗ 실제 운영 시 주의

# 3. 임의의 5명 생성
sample_users = [
    {
        "userid": f"user{i}",
        "username": f"유저{i}",
        "password": "hashed_password",
        "enter_time": datetime.now() - timedelta(hours=random.randint(1, 5)),
        "goal_time": random.randint(5, 10) * 3600,     # 목표 5~10시간
        "study_time": random.randint(1000, 20000)       # 누적 공부시간 (초)
    }
    for i in range(1, 6)
]

# 4. MongoDB에 삽입
users_collection.insert_many(sample_users)

print("✅ 테스트 유저 5명 삽입 완료!")
