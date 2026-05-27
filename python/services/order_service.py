"""订单数据服务 - 为用户生成模拟订单数据。

为每个预置用户生成 3-5 条历史订单，支持不同的订单状态。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

import random


OrderStatus = Literal["pending", "shipped", "delivered", "to_review"]

# 订单状态中文映射
ORDER_STATUS_CN = {
    "pending": "待发货",
    "shipped": "配送中",
    "delivered": "已完成",
    "to_review": "待评价",
}


class OrderItem:
    """订单中的商品项。"""

    def __init__(
        self,
        product_id: str,
        name: str,
        quantity: int,
        price: float,
    ):
        self.product_id = product_id
        self.name = name
        self.quantity = quantity
        self.price = price

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
            "subtotal": round(self.quantity * self.price, 2),
        }


class Order:
    """订单数据结构。"""

    def __init__(
        self,
        order_id: str,
        user_id: str,
        items: list[OrderItem],
        total_price: float,
        status: OrderStatus,
        order_time: str,  # ISO format
        delivery_address: str = "",
        estimated_delivery: str | None = None,
        actual_delivery: str | None = None,
    ):
        self.order_id = order_id
        self.user_id = user_id
        self.items = items
        self.total_price = total_price
        self.status = status
        self.order_time = order_time
        self.delivery_address = delivery_address
        self.estimated_delivery = estimated_delivery
        self.actual_delivery = actual_delivery

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "total_price": round(self.total_price, 2),
            "status": self.status,
            "status_cn": ORDER_STATUS_CN.get(self.status, self.status),
            "order_time": self.order_time,
            "delivery_address": self.delivery_address,
            "estimated_delivery": self.estimated_delivery,
            "actual_delivery": self.actual_delivery,
        }


# ════════════════════════════════════════════════════════════════
# 模拟数据：商品库
# ════════════════════════════════════════════════════════════════

# 商品库（product_id -> (name, price)）
PRODUCT_CATALOG = {
    "P001": ("iPhone 16 Pro", 7999),
    "P002": ("华为 Mate 70", 5999),
    "P003": ("小米 15", 3999),
    "P004": ("Samsung Galaxy S26", 6999),
    "P006": ("AirPods Pro 3", 1899),
    "P007": ("Sony WH-1000XM6", 2499),
    "P008": ("Bose QC Ultra", 2299),
    "P009": ("Redmi Buds 6 Pro", 399),
    "P011": ("iPad Air M3", 4799),
    "P012": ("小米平板 7 Pro", 2499),
    "P013": ("Galaxy Tab S10", 5499),
    "P016": ("Anker 140W 充电器", 399),
    "P019": ("罗技 MX Master 3S", 749),
    "P020": ("Keychron K3 Pro", 699),
    "P021": ("MacBook Air M4", 9999),
    "P022": ("Dell XPS 14", 10999),
    "P023": ("联想拯救者 Y9000P", 8999),
    "P026": ("戴尔 U2724D", 3299),
    "P027": ("LG 27GP850", 2399),
    "P029": ("华为 MateView SE", 1399),
    "P036": ("Apple Watch Ultra 3", 5999),
    "P037": ("华为 Watch GT 6", 1999),
}

# 配送地址模板
DELIVERY_ADDRESSES = [
    "北京市朝阳区建国路99号",
    "上海市浦东新区世纪大道1号",
    "深圳市南山区科技中路1号",
    "杭州市西湖区文三路153号",
    "成都市高新区天府大道北段366号",
    "广州市天河区珠江新城西门路1号",
]


# ════════════════════════════════════════════════════════════════
# 订单服务
# ════════════════════════════════════════════════════════════════


class OrderService:
    """订单数据生成和管理服务。"""

    def __init__(self, seed: int | None = None):
        """
        初始化订单服务。
        
        Args:
            seed: 随机数种子，用于确保可复现性
        """
        if seed is not None:
            random.seed(seed)
        # 订单数据，按用户ID组织
        self._orders: dict[str, list[Order]] = {}
        self._order_count = 0

    def generate_orders_for_user(
        self, user_id: str, user_price_range: tuple[float, float], num_orders: int = 4
    ) -> list[Order]:
        """
        为某个用户生成订单数据。
        
        Args:
            user_id: 用户ID
            user_price_range: 用户的价格区间 (min, max)
            num_orders: 生成的订单数，默认4条（3-5条）
        
        Returns:
            订单列表
        """
        if user_id in self._orders:
            return self._orders[user_id]

        num_orders = max(3, min(5, num_orders))  # 确保在 3-5 之间
        orders = []
        now = datetime.now()

        for i in range(num_orders):
            # 订单时间：从最近到最远（最近的在1周内，最远的在3个月内）
            order_index = i
            if order_index == 0:
                days_ago = random.randint(0, 7)  # 最新订单：1周内
            elif order_index == 1:
                days_ago = random.randint(7, 30)  # 次新订单：1个月内
            else:
                days_ago = random.randint(30, 90)  # 较早订单：3个月内

            order_time = (now - timedelta(days=days_ago)).isoformat()

            # 根据用户价格区间选择商品
            eligible_products = [
                (pid, name, price)
                for pid, (name, price) in PRODUCT_CATALOG.items()
                if user_price_range[0] <= price <= user_price_range[1]
            ]

            if not eligible_products:
                # 如果没有符合价格区间的商品，使用全部商品
                eligible_products = [
                    (pid, name, price) for pid, (name, price) in PRODUCT_CATALOG.items()
                ]

            # 生成订单项（1-3个商品）
            num_items = random.randint(1, 3)
            selected = random.sample(eligible_products, min(num_items, len(eligible_products)))
            items = [
                OrderItem(
                    product_id=pid,
                    name=name,
                    quantity=random.randint(1, 2),
                    price=price,
                )
                for pid, name, price in selected
            ]

            total_price = sum(item.quantity * item.price for item in items)

            # 订单状态分布
            # 最新订单：待发货、配送中
            # 较早订单：已完成、待评价
            if order_index == 0:
                status = random.choice(["pending", "shipped"])
                estimated_delivery = (now + timedelta(days=random.randint(1, 3))).isoformat()
                actual_delivery = None
            else:
                status = random.choice(["delivered", "to_review"])
                estimated_delivery = (now - timedelta(days=days_ago - random.randint(2, 5))).isoformat()
                actual_delivery = (now - timedelta(days=days_ago - random.randint(0, 3))).isoformat()

            order = Order(
                order_id=f"{user_id}_O{i+1:02d}",
                user_id=user_id,
                items=items,
                total_price=total_price,
                status=status,
                order_time=order_time,
                delivery_address=random.choice(DELIVERY_ADDRESSES),
                estimated_delivery=estimated_delivery,
                actual_delivery=actual_delivery,
            )
            orders.append(order)
            self._order_count += 1

        # 按订单时间倒序排列（最新的在前）
        orders.sort(key=lambda o: o.order_time, reverse=True)

        self._orders[user_id] = orders
        return orders

    def get_user_orders(
        self, user_id: str, status: OrderStatus | None = None, page: int = 1, page_size: int = 5
    ) -> tuple[list[Order], int]:
        """
        获取用户订单，支持按状态筛选和分页。
        
        Args:
            user_id: 用户ID
            status: 订单状态筛选，None表示不筛选
            page: 页码（1-based）
            page_size: 每页条数
        
        Returns:
            (订单列表, 总数)
        """
        if user_id not in self._orders:
            return [], 0

        orders = self._orders[user_id]

        # 按状态筛选
        if status is not None:
            filtered = [o for o in orders if o.status == status]
        else:
            filtered = orders

        # 分页
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

        return paged, total

    def get_order_detail(self, order_id: str) -> Order | None:
        """
        获取订单详情。
        
        Args:
            order_id: 订单ID
        
        Returns:
            订单数据，如果不存在返回 None
        """
        # order_id 格式：{user_id}_O{index}
        parts = order_id.split("_O")
        if len(parts) != 2:
            return None

        user_id = parts[0]
        if user_id not in self._orders:
            return None

        for order in self._orders[user_id]:
            if order.order_id == order_id:
                return order

        return None

    def create_order(
        self,
        user_id: str,
        items: list[dict[str, Any]],
        total_price: float,
        delivery_address: str = "",
    ) -> Order:
        """
        创建新订单。
        
        Args:
            user_id: 用户ID
            items: 订单项列表，每项包含 product_id, name, quantity, price
            total_price: 订单总价
            delivery_address: 配送地址
        
        Returns:
            创建的订单对象
        """
        if user_id not in self._orders:
            self._orders[user_id] = []

        # 生成订单ID
        order_index = len(self._orders[user_id]) + 1
        order_id = f"{user_id}_O{order_index:02d}"

        # 转换 items
        order_items = [
            OrderItem(
                product_id=item["product_id"],
                name=item["name"],
                quantity=item["quantity"],
                price=item["price"],
            )
            for item in items
        ]

        # 新订单默认为待发货状态
        now = datetime.now()
        order = Order(
            order_id=order_id,
            user_id=user_id,
            items=order_items,
            total_price=total_price,
            status="pending",
            order_time=now.isoformat(),
            delivery_address=delivery_address or random.choice(DELIVERY_ADDRESSES),
            estimated_delivery=(now + timedelta(days=random.randint(1, 3))).isoformat(),
        )

        self._orders[user_id].append(order)
        self._order_count += 1

        return order


# ════════════════════════════════════════════════════════════════
# 全局订单服务实例
# ════════════════════════════════════════════════════════════════

_order_service: OrderService | None = None


def get_order_service() -> OrderService:
    """获取全局订单服务实例（单例模式）。"""
    global _order_service
    if _order_service is None:
        _order_service = OrderService(seed=42)  # 使用固定种子确保可复现
    return _order_service
