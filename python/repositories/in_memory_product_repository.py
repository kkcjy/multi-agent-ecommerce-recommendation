"""In-memory product repository implementation."""

from __future__ import annotations

from models.schemas import InventoryStatus, Product

from .product_repository import ProductRepository


# Mock 数据移到这里 - 从原来的 product_rec_agent.py 迁移
def _inventory_status(stock: int) -> InventoryStatus:
    if stock <= 0:
        return InventoryStatus.OUT_OF_STOCK
    if stock <= 60:
        return InventoryStatus.LOW_STOCK
    return InventoryStatus.IN_STOCK


def _price_tags(tags: list[str], final_price: float, discount: float, status: InventoryStatus) -> list[str]:
    output: list[str] = []
    if discount > 0:
        output.append("discount")
    if final_price <= 199:
        output.append("value")
    if "新品" in tags:
        output.append("new")
    if status == InventoryStatus.LOW_STOCK:
        output.append("low_stock")
    return output


def _badges(tags: list[str], sales: int, status: InventoryStatus) -> list[str]:
    output: list[str] = []
    if "新品" in tags:
        output.append("new")
    if "旗舰" in tags:
        output.append("flagship")
    if sales >= 6000:
        output.append("hot")
    if status == InventoryStatus.LOW_STOCK:
        output.append("low_stock")
    return output


def _make_product(
    product_id: str,
    name: str,
    category: str,
    price: float,
    *,
    discount: float = 0.0,
    brand: str = "",
    seller_id: str = "S01",
    stock: int = 0,
    tags: list[str] | None = None,
    sales: int = 0,
    rating: float = 0.0,
    review_count: int = 0,
    image_url: str = "",
    external_url: str = "",
    specs: dict | None = None,
) -> Product:
    safe_tags = tags or []
    final_price = round(price - discount, 2) if discount else price
    status = _inventory_status(stock)
    return Product(
        product_id=product_id,
        name=name,
        category=category,
        price=price,
        final_price=final_price,
        discount=discount,
        original_price=price,
        brand=brand,
        seller_id=seller_id,
        stock=stock,
        inventory_status=status,
        sales=sales,
        rating=rating,
        review_count=review_count,
        tags=safe_tags,
        price_tags=_price_tags(safe_tags, final_price, discount, status),
        badges=_badges(safe_tags, sales, status),
        image_url=image_url,
        external_url=external_url,
        specs=specs or {},
        score=rating,
    )


MOCK_PRODUCTS = [
    _make_product(
        "P001",
        "iPhone 16 Pro",
        "手机",
        7999,
        discount=500,
        brand="Apple",
        stock=520,
        tags=["旗舰", "新品"],
        sales=9800,
        rating=4.9,
        review_count=18234,
        external_url="https://example.com/products/P001",
        specs={"storage": "256GB", "color": "Titanium"},
    ),
    _make_product(
        "P002",
        "华为 Mate 70",
        "手机",
        5999,
        discount=300,
        brand="华为",
        stock=340,
        tags=["旗舰", "国产"],
        sales=7600,
        rating=4.7,
        review_count=12980,
        external_url="https://example.com/products/P002",
        specs={"storage": "256GB", "color": "雅黑"},
    ),
    _make_product(
        "P003",
        "小米 15",
        "手机",
        3999,
        discount=200,
        brand="小米",
        stock=880,
        tags=["性价比", "新品"],
        sales=6800,
        rating=4.6,
        review_count=9040,
    ),
    _make_product(
        "P004",
        "Samsung Galaxy S26",
        "手机",
        6999,
        discount=400,
        brand="Samsung",
        stock=210,
        tags=["旗舰"],
        sales=5200,
        rating=4.5,
        review_count=6120,
    ),
    _make_product(
        "P005",
        "OnePlus 13",
        "手机",
        4299,
        discount=180,
        brand="OnePlus",
        stock=460,
        tags=["游戏", "快充"],
        sales=4100,
        rating=4.4,
        review_count=3880,
    ),
    _make_product(
        "P006",
        "AirPods Pro 3",
        "耳机",
        1899,
        discount=150,
        brand="Apple",
        stock=1200,
        tags=["降噪", "无线", "新品"],
        sales=8600,
        rating=4.8,
        review_count=14220,
    ),
    _make_product(
        "P007",
        "Sony WH-1000XM6",
        "耳机",
        2499,
        discount=280,
        brand="Sony",
        stock=260,
        tags=["头戴", "降噪"],
        sales=5200,
        rating=4.7,
        review_count=7040,
    ),
    _make_product(
        "P008",
        "Bose QC Ultra",
        "耳机",
        2299,
        discount=200,
        brand="Bose",
        stock=180,
        tags=["降噪", "舒适"],
        sales=3900,
        rating=4.6,
        review_count=4550,
    ),
    _make_product(
        "P009",
        "Redmi Buds 6 Pro",
        "耳机",
        399,
        discount=80,
        brand="Redmi",
        stock=1600,
        tags=["性价比", "降噪"],
        sales=9200,
        rating=4.5,
        review_count=11780,
    ),
    _make_product(
        "P010",
        "Beats Studio Buds+",
        "耳机",
        1099,
        discount=200,
        brand="Beats",
        stock=420,
        tags=["运动", "无线"],
        sales=3100,
        rating=4.3,
        review_count=2680,
    ),
    _make_product(
        "P011",
        "iPad Air M3",
        "平板",
        4799,
        discount=300,
        brand="Apple",
        stock=440,
        tags=["学习", "办公"],
        sales=5400,
        rating=4.7,
        review_count=7420,
    ),
    _make_product(
        "P012",
        "小米平板 7 Pro",
        "平板",
        2499,
        discount=200,
        brand="小米",
        stock=620,
        tags=["娱乐", "性价比"],
        sales=6700,
        rating=4.5,
        review_count=6650,
    ),
    _make_product(
        "P013",
        "Galaxy Tab S10",
        "平板",
        5499,
        discount=400,
        brand="Samsung",
        stock=240,
        tags=["旗舰", "办公"],
        sales=3600,
        rating=4.4,
        review_count=3020,
    ),
    _make_product(
        "P014",
        "MatePad Pro 13",
        "平板",
        5299,
        discount=480,
        brand="华为",
        stock=260,
        tags=["绘画", "办公"],
        sales=3300,
        rating=4.4,
        review_count=2880,
    ),
    _make_product(
        "P015",
        "联想小新 Pad 2025",
        "平板",
        1999,
        discount=150,
        brand="联想",
        stock=700,
        tags=["学习", "性价比"],
        sales=5200,
        rating=4.3,
        review_count=4120,
    ),
    _make_product(
        "P016",
        "Anker 140W 充电器",
        "配件",
        399,
        discount=60,
        brand="Anker",
        stock=2100,
        tags=["快充", "便携"],
        sales=12000,
        rating=4.8,
        review_count=15600,
    ),
    _make_product(
        "P017",
        "绿联氮化镓 65W",
        "配件",
        129,
        discount=20,
        brand="绿联",
        stock=5200,
        tags=["快充", "性价比"],
        sales=21000,
        rating=4.7,
        review_count=22040,
    ),
    _make_product(
        "P018",
        "倍思 10000mAh 移动电源",
        "配件",
        199,
        discount=30,
        brand="倍思",
        stock=2400,
        tags=["便携", "旅行"],
        sales=9800,
        rating=4.6,
        review_count=9020,
    ),
    _make_product(
        "P019",
        "罗技 MX Master 3S",
        "配件",
        749,
        discount=100,
        brand="Logitech",
        stock=520,
        tags=["无线", "办公"],
        sales=4800,
        rating=4.8,
        review_count=6340,
    ),
    _make_product(
        "P020",
        "Keychron K3 Pro",
        "配件",
        699,
        discount=80,
        brand="Keychron",
        stock=380,
        tags=["机械", "办公"],
        sales=2900,
        rating=4.4,
        review_count=2480,
    ),
    _make_product(
        "P021",
        "MacBook Air M4",
        "笔记本",
        9999,
        discount=800,
        brand="Apple",
        stock=140,
        tags=["轻薄", "办公", "新品"],
        sales=5100,
        rating=4.8,
        review_count=6890,
        specs={"memory": "16GB", "storage": "512GB"},
    ),
    _make_product(
        "P022",
        "Dell XPS 14",
        "笔记本",
        10999,
        discount=900,
        brand="Dell",
        stock=120,
        tags=["旗舰", "办公"],
        sales=3200,
        rating=4.6,
        review_count=3500,
    ),
    _make_product(
        "P023",
        "联想拯救者 Y9000P",
        "笔记本",
        8999,
        discount=700,
        brand="联想",
        stock=210,
        tags=["游戏", "高性能"],
        sales=4300,
        rating=4.5,
        review_count=4120,
    ),
    _make_product(
        "P024",
        "ROG 幻14 2025",
        "笔记本",
        12999,
        discount=1000,
        brand="ASUS",
        stock=90,
        tags=["游戏", "轻薄"],
        sales=2600,
        rating=4.4,
        review_count=2180,
    ),
    _make_product(
        "P025",
        "机械革命 极光 X",
        "笔记本",
        6999,
        discount=500,
        brand="机械革命",
        stock=160,
        tags=["游戏", "性价比"],
        sales=3800,
        rating=4.3,
        review_count=1980,
    ),
    _make_product(
        "P026",
        "戴尔 U2724D 显示器",
        "显示器",
        3299,
        discount=300,
        brand="Dell",
        stock=70,
        tags=["4K", "办公"],
        sales=2200,
        rating=4.6,
        review_count=1550,
    ),
    _make_product(
        "P027",
        "LG 27GP850",
        "显示器",
        2399,
        discount=200,
        brand="LG",
        stock=110,
        tags=["电竞", "高刷"],
        sales=3600,
        rating=4.5,
        review_count=2860,
    ),
    _make_product(
        "P028",
        "AOC 24G2",
        "显示器",
        1099,
        discount=100,
        brand="AOC",
        stock=260,
        tags=["电竞", "性价比"],
        sales=6800,
        rating=4.4,
        review_count=4550,
    ),
    _make_product(
        "P029",
        "华为 MateView SE",
        "显示器",
        1399,
        discount=150,
        brand="华为",
        stock=190,
        tags=["护眼", "办公"],
        sales=3200,
        rating=4.3,
        review_count=1880,
    ),
    _make_product(
        "P030",
        "小米 34 曲面",
        "显示器",
        2199,
        discount=200,
        brand="小米",
        stock=150,
        tags=["大屏", "娱乐"],
        sales=3000,
        rating=4.2,
        review_count=1640,
    ),
    _make_product(
        "P031",
        "三星 990 Pro 2TB",
        "存储",
        1199,
        discount=150,
        brand="三星",
        stock=320,
        tags=["SSD", "高速"],
        sales=5400,
        rating=4.7,
        review_count=4880,
    ),
    _make_product(
        "P032",
        "WD SN850X 1TB",
        "存储",
        799,
        discount=100,
        brand="WD",
        stock=280,
        tags=["SSD", "游戏"],
        sales=4200,
        rating=4.6,
        review_count=3620,
    ),
    _make_product(
        "P033",
        "Kingston NV3 2TB",
        "存储",
        699,
        discount=80,
        brand="Kingston",
        stock=540,
        tags=["SSD", "性价比"],
        sales=6100,
        rating=4.5,
        review_count=4120,
    ),
    _make_product(
        "P034",
        "SanDisk Extreme 1TB",
        "存储",
        699,
        discount=70,
        brand="SanDisk",
        stock=430,
        tags=["便携", "高速"],
        sales=3500,
        rating=4.5,
        review_count=2680,
    ),
    _make_product(
        "P035",
        "希捷 Backup Plus 4TB",
        "存储",
        899,
        discount=120,
        brand="Seagate",
        stock=220,
        tags=["大容量", "备份"],
        sales=2900,
        rating=4.3,
        review_count=1760,
    ),
    _make_product(
        "P036",
        "Apple Watch Ultra 3",
        "穿戴",
        5999,
        discount=500,
        brand="Apple",
        stock=210,
        tags=["运动", "健康"],
        sales=4100,
        rating=4.7,
        review_count=5200,
    ),
    _make_product(
        "P037",
        "华为 Watch GT 6",
        "穿戴",
        1999,
        discount=200,
        brand="华为",
        stock=340,
        tags=["健康", "续航"],
        sales=4700,
        rating=4.5,
        review_count=3920,
    ),
    _make_product(
        "P038",
        "Garmin Fenix 8",
        "穿戴",
        7499,
        discount=600,
        brand="Garmin",
        stock=60,
        tags=["户外", "专业"],
        sales=1800,
        rating=4.6,
        review_count=1280,
    ),
    _make_product(
        "P039",
        "小米 Watch S4",
        "穿戴",
        1299,
        discount=100,
        brand="小米",
        stock=520,
        tags=["性价比", "运动"],
        sales=5200,
        rating=4.4,
        review_count=4020,
    ),
    _make_product(
        "P040",
        "Oura Ring Gen4",
        "穿戴",
        2999,
        discount=300,
        brand="Oura",
        stock=90,
        tags=["睡眠", "健康"],
        sales=1400,
        rating=4.2,
        review_count=860,
    ),
    _make_product(
        "P041",
        "大疆 Mini 4 Pro",
        "无人机",
        4788,
        discount=400,
        brand="大疆",
        stock=120,
        tags=["航拍", "便携"],
        sales=2600,
        rating=4.7,
        review_count=2120,
    ),
    _make_product(
        "P042",
        "大疆 Air 4S",
        "无人机",
        6888,
        discount=500,
        brand="大疆",
        stock=80,
        tags=["航拍", "旗舰"],
        sales=2100,
        rating=4.6,
        review_count=1480,
    ),
    _make_product(
        "P043",
        "Autel EVO Nano+",
        "无人机",
        3599,
        discount=300,
        brand="Autel",
        stock=90,
        tags=["便携", "性价比"],
        sales=1700,
        rating=4.3,
        review_count=820,
    ),
    _make_product(
        "P044",
        "Switch 2",
        "游戏机",
        2499,
        discount=200,
        brand="Nintendo",
        stock=50,
        tags=["新品", "游戏"],
        sales=9000,
        rating=4.8,
        review_count=12100,
    ),
    _make_product(
        "P045",
        "PlayStation 5 Pro",
        "游戏机",
        4499,
        discount=300,
        brand="Sony",
        stock=0,
        tags=["旗舰", "游戏"],
        sales=7400,
        rating=4.7,
        review_count=8650,
    ),
    _make_product(
        "P046",
        "Xbox Series X2",
        "游戏机",
        4299,
        discount=300,
        brand="Microsoft",
        stock=110,
        tags=["游戏", "旗舰"],
        sales=5200,
        rating=4.6,
        review_count=6020,
    ),
    _make_product(
        "P047",
        "Steam Deck OLED",
        "游戏机",
        3799,
        discount=200,
        brand="Valve",
        stock=140,
        tags=["掌机", "游戏"],
        sales=4300,
        rating=4.5,
        review_count=3580,
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
            self._products, key=lambda p: (p.sales, p.stock), reverse=True
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
