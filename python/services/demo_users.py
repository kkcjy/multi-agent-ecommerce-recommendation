"""预置演示用户数据模块。

为课堂演示提供 6 个差异化用户，覆盖不同画像分群。
每个用户有独立的偏好、浏览历史和购买记录，切换后推荐结果会明显不同。
"""

from __future__ import annotations

from typing import Any

from models.schemas import UserSegment


class DemoUser:
    """演示用户数据结构。"""

    def __init__(
        self,
        user_id: str,
        nickname: str,
        avatar: str,
        age: int,
        gender: str,
        city: str,
        segments: list[str],
        preferred_categories: list[str],
        price_range: tuple[float, float],
        recent_views: list[str],
        recent_purchases: list[str],
        rfm_score: dict[str, float],
        login_count: int,
        register_time: str,
        description: str = "",
    ):
        self.user_id = user_id
        self.nickname = nickname
        self.avatar = avatar
        self.age = age
        self.gender = gender
        self.city = city
        self.segments = segments
        self.preferred_categories = preferred_categories
        self.price_range = price_range
        self.recent_views = recent_views
        self.recent_purchases = recent_purchases
        self.rfm_score = rfm_score
        self.login_count = login_count
        self.register_time = register_time
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "age": self.age,
            "gender": self.gender,
            "city": self.city,
            "segments": self.segments,
            "preferred_categories": self.preferred_categories,
            "price_range": list(self.price_range),
            "recent_views": self.recent_views,
            "recent_purchases": self.recent_purchases,
            "rfm_score": self.rfm_score,
            "login_count": self.login_count,
            "register_time": self.register_time,
            "description": self.description,
        }

    def to_summary(self) -> dict[str, Any]:
        """轻量摘要，用于用户列表。"""
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "age": self.age,
            "city": self.city,
            "segments": self.segments,
            "preferred_categories": self.preferred_categories,
            "description": self.description,
        }

    def to_profile_dict(self) -> dict[str, Any]:
        """转为 UserProfile schema 兼容的字典。"""
        return {
            "user_id": self.user_id,
            "age": self.age,
            "gender": self.gender,
            "city": self.city,
            "segments": self.segments,
            "preferred_categories": self.preferred_categories,
            "price_range": list(self.price_range),
            "recent_views": self.recent_views,
            "recent_purchases": self.recent_purchases,
            "rfm_score": self.rfm_score,
        }


# ================================================================
# 6 个差异化预置用户
# ================================================================

DEMO_USERS: list[DemoUser] = [
    DemoUser(
        user_id="demo_tech",
        nickname="数码极客·张伟",
        avatar="🧑‍💻",
        age=28,
        gender="男",
        city="北京",
        segments=[UserSegment.HIGH_VALUE.value],
        preferred_categories=["手机", "笔记本", "配件"],
        price_range=(5000.0, 15000.0),
        recent_views=["P001", "P002", "P021"],
        recent_purchases=["P001", "P021", "P006"],
        rfm_score={"recency": 0.9, "frequency": 0.85, "monetary": 0.92},
        login_count=156,
        register_time="2024-03-15",
        description="高频消费数码爱好者，偏好旗舰新品",
    ),
    DemoUser(
        user_id="demo_student",
        nickname="校园达人·李明",
        avatar="🎓",
        age=21,
        gender="男",
        city="上海",
        segments=[UserSegment.PRICE_SENSITIVE.value],
        preferred_categories=["手机", "耳机", "平板"],
        price_range=(500.0, 4000.0),
        recent_views=["P003", "P009", "P012"],
        recent_purchases=["P009", "P012"],
        rfm_score={"recency": 0.6, "frequency": 0.45, "monetary": 0.35},
        login_count=42,
        register_time="2025-09-01",
        description="学生用户，注重性价比",
    ),
    DemoUser(
        user_id="demo_worker",
        nickname="都市白领·王芳",
        avatar="👩‍💼",
        age=32,
        gender="女",
        city="深圳",
        segments=[UserSegment.ACTIVE.value],
        preferred_categories=["配件", "显示器", "穿戴"],
        price_range=(2000.0, 8000.0),
        recent_views=["P019", "P026", "P036"],
        recent_purchases=["P019", "P026"],
        rfm_score={"recency": 0.75, "frequency": 0.7, "monetary": 0.68},
        login_count=89,
        register_time="2024-07-20",
        description="办公效率追求者，注重品质与体验",
    ),
    DemoUser(
        user_id="demo_sport",
        nickname="运动达人·赵强",
        avatar="🏃",
        age=26,
        gender="男",
        city="成都",
        segments=[UserSegment.ACTIVE.value],
        preferred_categories=["穿戴", "耳机"],
        price_range=(1500.0, 6000.0),
        recent_views=["P037", "P007", "P039"],
        recent_purchases=["P037", "P007"],
        rfm_score={"recency": 0.8, "frequency": 0.6, "monetary": 0.55},
        login_count=67,
        register_time="2025-01-10",
        description="运动健康爱好者，关注穿戴设备",
    ),
    DemoUser(
        user_id="demo_newbie",
        nickname="萌新用户·陈静",
        avatar="🌟",
        age=19,
        gender="女",
        city="杭州",
        segments=[UserSegment.NEW_USER.value],
        preferred_categories=["手机", "耳机"],
        price_range=(500.0, 2000.0),
        recent_views=["P003", "P009"],
        recent_purchases=[],
        rfm_score={"recency": 0.3, "frequency": 0.1, "monetary": 0.05},
        login_count=5,
        register_time="2026-05-01",
        description="新注册用户，初次探索平台",
    ),
    DemoUser(
        user_id="demo_return",
        nickname="回归用户·刘洋",
        avatar="🔄",
        age=35,
        gender="男",
        city="广州",
        segments=[UserSegment.CHURN_RISK.value],
        preferred_categories=["笔记本", "显示器"],
        price_range=(3000.0, 10000.0),
        recent_views=["P022", "P029"],
        recent_purchases=["P022"],
        rfm_score={"recency": 0.2, "frequency": 0.3, "monetary": 0.45},
        login_count=23,
        register_time="2024-11-05",
        description="流失风险用户，需要召回激励",
    ),
]

# 构建 user_id → DemoUser 快速查找表
_DEMO_USER_MAP: dict[str, DemoUser] = {u.user_id: u for u in DEMO_USERS}


def get_all_demo_users() -> list[DemoUser]:
    """返回所有预置用户。"""
    return DEMO_USERS


def get_demo_user(user_id: str) -> DemoUser | None:
    """根据 user_id 获取预置用户，不存在则返回 None。"""
    return _DEMO_USER_MAP.get(user_id)


def is_demo_user(user_id: str) -> bool:
    """判断是否为预置用户。"""
    return user_id in _DEMO_USER_MAP
