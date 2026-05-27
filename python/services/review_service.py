"""评价数据服务 - 为商品生成模拟评价数据。

为每个商品生成 5-8 条真实风格的模拟评价，支持按评分筛选。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import random


class Review:
    """单条评价数据结构。"""

    def __init__(
        self,
        review_id: str,
        product_id: str,
        user_nickname: str,
        rating: int,  # 1-5
        content: str,
        review_time: str,  # ISO format
        helpful_count: int = 0,
        user_avatar: str = "",
    ):
        self.review_id = review_id
        self.product_id = product_id
        self.user_nickname = user_nickname
        self.rating = rating
        self.content = content
        self.review_time = review_time
        self.helpful_count = helpful_count
        self.user_avatar = user_avatar

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "review_id": self.review_id,
            "product_id": self.product_id,
            "user_nickname": self.user_nickname,
            "rating": self.rating,
            "content": self.content,
            "review_time": self.review_time,
            "helpful_count": self.helpful_count,
            "user_avatar": self.user_avatar,
        }


class ReviewSummary:
    """评价汇总数据。"""

    def __init__(
        self,
        product_id: str,
        average_rating: float,
        total_count: int,
        rating_distribution: dict[int, int],
        positive_rate: float,
    ):
        self.product_id = product_id
        self.average_rating = average_rating
        self.total_count = total_count
        self.rating_distribution = rating_distribution
        self.positive_rate = positive_rate

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "product_id": self.product_id,
            "average_rating": round(self.average_rating, 2),
            "total_count": self.total_count,
            "rating_distribution": self.rating_distribution,
            "positive_rate": round(self.positive_rate, 2),
        }


# ════════════════════════════════════════════════════════════════
# 评价模板库 - 按评分段分类
# ════════════════════════════════════════════════════════════════

REVIEW_TEMPLATES = {
    5: [
        "非常满意，质量非常好，物流速度也很快！",
        "超出预期，产品质量超级棒，强烈推荐！",
        "完全满意，包装很精致，用起来很流畅。",
        "品质一流，性能很强，性价比也很高。",
        "太值了！功能齐全，外观精美，很喜欢。",
        "效果很棒，收货速度快，服务态度也很好。",
        "买了这么多次，这次最满意！推荐购买。",
        "真的很好用，朋友也买了一个，都很满意。",
    ],
    4: [
        "很不错，质量还可以，就是配件有点少。",
        "基本满意，性能也不错，就是价格有点小贵。",
        "挺好的，功能完整，就是有点重。",
        "不错的选择，用起来很顺手，偶尔有小bug。",
        "满意度很高，就是续航时间可以再长一点。",
        "整体不错，包装有点损伤但产品完好。",
        "好产品，值得购买，发货也很快。",
        "性能可以，就是操作界面可以更简洁一些。",
    ],
    3: [
        "一般般，功能齐全但还有改进空间。",
        "中规中矩，及格线水准，没有太大亮点。",
        "可以接受，就是有些细节不够完美。",
        "基本符合预期，但没有惊喜。",
        "还不错，就是和宣传有点不一样。",
        "质量还行，但对比竞品没什么优势。",
        "一般般，用着还可以，就是没什么特色。",
        "还好啦，虽然不是最好的，但也不坏。",
    ],
    2: [
        "不太满意，质量一般，性价比不高。",
        "有点失望，用了几天就出现问题了。",
        "品质不如想象的好，有点后悔买了。",
        "一般般，和介绍的不太一样。",
        "有缺陷，用起来不太顺手，客服态度也一般。",
        "不推荐，虽然便宜但质量真的一般。",
        "有点问题，虽然能用但不是很稳定。",
        "失望了，没想到质量这么一般。",
    ],
    1: [
        "完全失望，收到的产品有破损，质量极差！",
        "非常后悔，用了一天就坏了，简直是浪费钱。",
        "太差了，和图片完全不一样，退货麻烦死了。",
        "质量太差，这个价格买这个东西太亏了！",
        "非常不满意，根本不值这个价钱，绝对不推荐。",
        "垃圾产品，用了不到一周就坏掉了。",
        "真后悔买这个，各种小问题，客服也不理。",
        "最差的购物体验，钱打水漂了。",
    ],
}

USER_NICKNAMES = [
    "玩转数码的小张",
    "上班族小王",
    "95后美女小李",
    "高中学生小刘",
    "宝妈日记",
    "资深发烧友",
    "专业评测员",
    "上班一族",
    "学生党",
    "年轻妈妈",
    "科技爱好者",
    "运动达人",
    "办公室达人",
    "手机发烧友",
    "电商老司机",
]

USER_AVATARS = ["👨", "👩", "👨‍💼", "👩‍💼", "👨‍🎓", "👩‍🎓", "🧑", "👨‍💻", "👩‍💻"]


# ════════════════════════════════════════════════════════════════
# 评价服务
# ════════════════════════════════════════════════════════════════


class ReviewService:
    """评价数据生成和管理服务。"""

    def __init__(self, seed: int | None = None):
        """
        初始化评价服务。
        
        Args:
            seed: 随机数种子，用于确保可复现性
        """
        if seed is not None:
            random.seed(seed)
        # 为每个商品预生成评价数据，存储在内存中
        self._reviews: dict[str, list[Review]] = {}
        self._review_count = 0

    def generate_reviews_for_product(
        self, product_id: str, product_rating: float, review_count: int, num_reviews: int = 6
    ) -> list[Review]:
        """
        为某个商品生成评价数据。
        
        Args:
            product_id: 商品ID
            product_rating: 商品评分（用于决定评价分布）
            review_count: 商品评价数（用于时间分布）
            num_reviews: 生成的评价条数，默认6条（5-8条）
        
        Returns:
            评价列表
        """
        if product_id in self._reviews:
            return self._reviews[product_id]

        num_reviews = max(5, min(8, num_reviews))  # 确保在 5-8 之间

        reviews = []
        
        # 根据商品评分分布生成评价评分
        # 例如商品评分4.8，应该大部分是5星，少数4星或3星
        ratings = self._generate_rating_distribution(product_rating, num_reviews)

        # 生成时间分布：最近的评价距离现在最近，最早的评价距离现在最远
        now = datetime.now()
        time_offsets = self._generate_time_distribution(review_count, num_reviews)

        for i in range(num_reviews):
            rating = ratings[i]
            time_offset = time_offsets[i]
            review_time = (now - timedelta(days=time_offset)).isoformat()

            review = Review(
                review_id=f"{product_id}_R{i+1:02d}",
                product_id=product_id,
                user_nickname=random.choice(USER_NICKNAMES),
                rating=rating,
                content=random.choice(REVIEW_TEMPLATES[rating]),
                review_time=review_time,
                helpful_count=random.randint(0, 200) if rating >= 4 else random.randint(0, 50),
                user_avatar=random.choice(USER_AVATARS),
            )
            reviews.append(review)
            self._review_count += 1

        # 按时间倒序排列（最新的在前）
        reviews.sort(key=lambda r: r.review_time, reverse=True)
        
        self._reviews[product_id] = reviews
        return reviews

    def get_reviews(
        self, product_id: str, min_rating: int | None = None, page: int = 1, page_size: int = 5
    ) -> tuple[list[Review], int]:
        """
        获取商品评价，支持按评分筛选和分页。
        
        Args:
            product_id: 商品ID
            min_rating: 最低评分（1-5），None表示不筛选
            page: 页码（1-based）
            page_size: 每页条数
        
        Returns:
            (评价列表, 总数)
        """
        if product_id not in self._reviews:
            return [], 0

        reviews = self._reviews[product_id]
        
        # 按评分筛选
        if min_rating is not None and 1 <= min_rating <= 5:
            filtered = [r for r in reviews if r.rating >= min_rating]
        else:
            filtered = reviews

        # 分页
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

        return paged, total

    def get_review_summary(self, product_id: str) -> ReviewSummary:
        """
        获取商品评价汇总。
        
        Args:
            product_id: 商品ID
        
        Returns:
            评价汇总数据
        """
        if product_id not in self._reviews:
            return ReviewSummary(
                product_id=product_id,
                average_rating=0.0,
                total_count=0,
                rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                positive_rate=0.0,
            )

        reviews = self._reviews[product_id]
        
        if not reviews:
            return ReviewSummary(
                product_id=product_id,
                average_rating=0.0,
                total_count=0,
                rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                positive_rate=0.0,
            )

        # 计算统计数据
        total = len(reviews)
        rating_sum = sum(r.rating for r in reviews)
        average = rating_sum / total
        
        distribution = {i: 0 for i in range(1, 6)}
        for review in reviews:
            distribution[review.rating] += 1

        positive = sum(distribution[4:6])  # 4星和5星
        positive_rate = positive / total if total > 0 else 0.0

        return ReviewSummary(
            product_id=product_id,
            average_rating=average,
            total_count=total,
            rating_distribution=distribution,
            positive_rate=positive_rate,
        )

    def _generate_rating_distribution(self, product_rating: float, num_reviews: int) -> list[int]:
        """
        根据商品评分生成评价分布。
        评分越高，越倾向生成高星级评价。
        """
        ratings = []
        
        # 按评分权重分布
        if product_rating >= 4.7:
            # 大部分5星，少数4星
            weights = {5: 0.7, 4: 0.2, 3: 0.1}
        elif product_rating >= 4.5:
            weights = {5: 0.6, 4: 0.3, 3: 0.1}
        elif product_rating >= 4.0:
            weights = {5: 0.4, 4: 0.4, 3: 0.2}
        elif product_rating >= 3.5:
            weights = {5: 0.2, 4: 0.4, 3: 0.3, 2: 0.1}
        else:
            weights = {5: 0.1, 4: 0.2, 3: 0.3, 2: 0.3, 1: 0.1}

        # 根据权重生成评分
        rating_list = []
        for rating, weight in weights.items():
            count = int(num_reviews * weight)
            rating_list.extend([rating] * count)

        # 补齐缺失的评价（舍入误差）
        while len(rating_list) < num_reviews:
            rating_list.append(random.choice(list(weights.keys())))

        # 随机打乱顺序
        random.shuffle(rating_list)
        return rating_list[:num_reviews]

    def _generate_time_distribution(self, review_count: int, num_reviews: int) -> list[int]:
        """
        生成评价时间分布。
        评价越多，时间跨度越长（可能跨越数个月）。
        """
        # 评价越多，时间跨度越长
        max_days = min(180, max(30, review_count // 100))  # 30-180 天范围
        
        offsets = []
        for _ in range(num_reviews):
            # 大部分评价集中在最近，少数评价很久以前
            if random.random() < 0.6:  # 60% 最近30天
                offset = random.randint(0, min(30, max_days))
            else:  # 40% 更早期
                offset = random.randint(30, max_days)
            offsets.append(offset)
        
        return offsets


# ════════════════════════════════════════════════════════════════
# 全局评价服务实例
# ════════════════════════════════════════════════════════════════

_review_service: ReviewService | None = None


def get_review_service() -> ReviewService:
    """获取全局评价服务实例（单例模式）。"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService(seed=42)  # 使用固定种子确保可复现
    return _review_service
