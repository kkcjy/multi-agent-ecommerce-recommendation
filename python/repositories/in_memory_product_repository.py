"""In-memory product repository implementation."""

from __future__ import annotations

from models.schemas import Product

from .product_repository import ProductRepository


# Mock 数据移到这里 - 从原来的 product_rec_agent.py 迁移
MOCK_PRODUCTS = [
    Product(
        product_id="P001",
        name="iPhone 16 Pro",
        category="手机",
        price=7999,
        brand="Apple",
        seller_id="S01",
        stock=500,
        tags=["旗舰", "新品"],
    ),
    Product(
        product_id="P002",
        name="华为 Mate 70",
        category="手机",
        price=5999,
        brand="华为",
        seller_id="S02",
        stock=300,
        tags=["旗舰", "国产"],
    ),
    Product(
        product_id="P003",
        name="AirPods Pro 3",
        category="耳机",
        price=1899,
        brand="Apple",
        seller_id="S01",
        stock=1000,
        tags=["降噪", "无线"],
    ),
    Product(
        product_id="P004",
        name="Sony WH-1000XM6",
        category="耳机",
        price=2499,
        brand="Sony",
        seller_id="S03",
        stock=200,
        tags=["头戴", "降噪"],
    ),
    Product(
        product_id="P005",
        name="iPad Air M3",
        category="平板",
        price=4799,
        brand="Apple",
        seller_id="S01",
        stock=400,
        tags=["学习", "办公"],
    ),
    Product(
        product_id="P006",
        name="小米平板 7 Pro",
        category="平板",
        price=2499,
        brand="小米",
        seller_id="S04",
        stock=600,
        tags=["性价比", "娱乐"],
    ),
    Product(
        product_id="P007",
        name="Anker 140W 充电器",
        category="配件",
        price=399,
        brand="Anker",
        seller_id="S05",
        stock=2000,
        tags=["快充", "便携"],
    ),
    Product(
        product_id="P008",
        name="机械革命极光 X",
        category="笔记本",
        price=6999,
        brand="机械革命",
        seller_id="S06",
        stock=150,
        tags=["游戏", "高性能"],
    ),
    Product(
        product_id="P009",
        name="戴尔 U2724D 显示器",
        category="显示器",
        price=3299,
        brand="Dell",
        seller_id="S07",
        stock=80,
        tags=["4K", "办公"],
    ),
    Product(
        product_id="P010",
        name="罗技 MX Master 3S",
        category="配件",
        price=749,
        brand="罗技",
        seller_id="S08",
        stock=500,
        tags=["无线", "办公"],
    ),
    Product(
        product_id="P011",
        name="三星 980 Pro 2TB",
        category="存储",
        price=1199,
        brand="三星",
        seller_id="S09",
        stock=300,
        tags=["SSD", "高速"],
    ),
    Product(
        product_id="P012",
        name="绿联氮化镓 65W",
        category="配件",
        price=129,
        brand="绿联",
        seller_id="S10",
        stock=5000,
        tags=["快充", "性价比"],
    ),
    Product(
        product_id="P013",
        name="Apple Watch Ultra 3",
        category="穿戴",
        price=5999,
        brand="Apple",
        seller_id="S01",
        stock=200,
        tags=["运动", "健康"],
    ),
    Product(
        product_id="P014",
        name="大疆 Mini 4 Pro",
        category="无人机",
        price=4788,
        brand="大疆",
        seller_id="S11",
        stock=100,
        tags=["航拍", "便携"],
    ),
    Product(
        product_id="P015",
        name="Switch 2",
        category="游戏机",
        price=2499,
        brand="Nintendo",
        seller_id="S12",
        stock=50,
        tags=["新品", "游戏"],
    ),
]


class InMemoryProductRepository(ProductRepository):
    """
    内存实现 - 用于开发和降级场景

    特点:
    - 使用静态 Mock 数据
    - 所有操作在内存中完成
    - 不会抛出异常，只返回空列表
    """

    def __init__(self, products: list[Product] | None = None):
        self._products = products if products is not None else list(MOCK_PRODUCTS)
        self._id_index = {p.product_id: p for p in self._products}
        self._category_index: dict[str, list[Product]] = {}
        for p in self._products:
            if p.category not in self._category_index:
                self._category_index[p.category] = []
            self._category_index[p.category].append(p)

    async def get_by_ids(self, ids: list[str]) -> list[Product]:
        """根据 ID 批量查询"""
        return [self._id_index[id_] for id_ in ids if id_ in self._id_index]

    async def get_by_category(self, category: str, limit: int = 10) -> list[Product]:
        """按类目查询"""
        products = self._category_index.get(category, [])
        return products[:limit]

    async def get_by_price_range(
        self, min_price: float, max_price: float, limit: int = 10
    ) -> list[Product]:
        """按价格区间查询"""
        products = [
            p for p in self._products if min_price <= p.price <= max_price
        ]
        return products[:limit]

    async def get_hot_products(self, limit: int = 10) -> list[Product]:
        """
        获取热门商品

        简化实现：按 stock 降序模拟热度
        生产环境可按销量/访问量排序
        """
        sorted_products = sorted(
            self._products, key=lambda p: p.stock, reverse=True
        )
        return sorted_products[:limit]

    async def get_new_products(self, limit: int = 10) -> list[Product]:
        """
        获取新品

        简化实现：按 tags 包含"新品"筛选
        生产环境可按上架时间排序
        """
        new_products = [p for p in self._products if "新品" in p.tags]
        return new_products[:limit]

    async def get_all_products(self, limit: int = 100) -> list[Product]:
        """获取所有商品"""
        return self._products[:limit]
