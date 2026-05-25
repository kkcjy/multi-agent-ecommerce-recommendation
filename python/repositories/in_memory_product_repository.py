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
    image_urls: list[str] | None = None,
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
        image_urls=image_urls or [image_url] if image_url else [],
        external_url=external_url,
        specs=specs or {},
        score=rating,
    )


# ── 精简后 22 款核心商品（7 品类） ──────────────────────────────
# 图片路径规则：
#   主图: /assets/images/products/{product_id}.jpg
#   多角度图: /assets/images/products/{product_id}_1.jpg, _2.jpg
#   品类兜底图: /assets/images/products/default_{category_en}.jpg
# 核心商品（有额外角度图）: P001-P004 (手机4), P006-P009 (耳机4), P011-P012 (平板2)

_IMG = "/assets/images/products"

MOCK_PRODUCTS = [
    # ═══ 手机 4 款 ═══
    _make_product(
        "P001", "iPhone 16 Pro", "手机", 7999, discount=500,
        brand="Apple", stock=520, tags=["旗舰", "新品"], sales=9800, rating=4.9, review_count=18234,
        image_url=f"{_IMG}/P001.jpg",
        image_urls=[f"{_IMG}/P001.jpg", f"{_IMG}/P001_1.jpg", f"{_IMG}/P001_2.jpg"],
        specs={"storage": "256GB", "color": "Titanium", "chip": "A18 Pro"},
    ),
    _make_product(
        "P002", "华为 Mate 70", "手机", 5999, discount=300,
        brand="华为", stock=340, tags=["旗舰", "国产"], sales=7600, rating=4.7, review_count=12980,
        image_url=f"{_IMG}/P002.jpg",
        image_urls=[f"{_IMG}/P002.jpg", f"{_IMG}/P002_1.jpg", f"{_IMG}/P002_2.jpg"],
        specs={"storage": "256GB", "color": "雅黑", "chip": "麒麟 9100"},
    ),
    _make_product(
        "P003", "小米 15", "手机", 3999, discount=200,
        brand="小米", stock=880, tags=["性价比", "新品"], sales=6800, rating=4.6, review_count=9040,
        image_url=f"{_IMG}/P003.jpg",
        image_urls=[f"{_IMG}/P003.jpg", f"{_IMG}/P003_1.jpg", f"{_IMG}/P003_2.jpg"],
        specs={"storage": "256GB", "color": "白色", "chip": "骁龙 8 Elite"},
    ),
    _make_product(
        "P004", "Samsung Galaxy S26", "手机", 6999, discount=400,
        brand="Samsung", stock=210, tags=["旗舰"], sales=5200, rating=4.5, review_count=6120,
        image_url=f"{_IMG}/P004.jpg",
        image_urls=[f"{_IMG}/P004.jpg", f"{_IMG}/P004_1.jpg", f"{_IMG}/P004_2.jpg"],
        specs={"storage": "256GB", "color": "钛灰", "chip": "Exynos 2500"},
    ),

    # ═══ 耳机 4 款 ═══
    _make_product(
        "P006", "AirPods Pro 3", "耳机", 1899, discount=150,
        brand="Apple", stock=1200, tags=["降噪", "无线", "新品"], sales=8600, rating=4.8, review_count=14220,
        image_url=f"{_IMG}/P006.jpg",
        image_urls=[f"{_IMG}/P006.jpg", f"{_IMG}/P006_1.jpg", f"{_IMG}/P006_2.jpg"],
        specs={"type": "入耳式", "battery": "6h+30h", "waterproof": "IP54"},
    ),
    _make_product(
        "P007", "Sony WH-1000XM6", "耳机", 2499, discount=280,
        brand="Sony", stock=260, tags=["头戴", "降噪"], sales=5200, rating=4.7, review_count=7040,
        image_url=f"{_IMG}/P007.jpg",
        image_urls=[f"{_IMG}/P007.jpg", f"{_IMG}/P007_1.jpg", f"{_IMG}/P007_2.jpg"],
        specs={"type": "头戴式", "battery": "40h", "noise_cancel": "双芯降噪"},
    ),
    _make_product(
        "P008", "Bose QC Ultra", "耳机", 2299, discount=200,
        brand="Bose", stock=180, tags=["降噪", "舒适"], sales=3900, rating=4.6, review_count=4550,
        image_url=f"{_IMG}/P008.jpg",
        image_urls=[f"{_IMG}/P008.jpg", f"{_IMG}/P008_1.jpg", f"{_IMG}/P008_2.jpg"],
        specs={"type": "头戴式", "battery": "24h", "noise_cancel": "自适应降噪"},
    ),
    _make_product(
        "P009", "Redmi Buds 6 Pro", "耳机", 399, discount=80,
        brand="Redmi", stock=1600, tags=["性价比", "降噪"], sales=9200, rating=4.5, review_count=11780,
        image_url=f"{_IMG}/P009.jpg",
        image_urls=[f"{_IMG}/P009.jpg", f"{_IMG}/P009_1.jpg", f"{_IMG}/P009_2.jpg"],
        specs={"type": "入耳式", "battery": "8h+30h", "waterproof": "IPX5"},
    ),

    # ═══ 平板 3 款 ═══
    _make_product(
        "P011", "iPad Air M3", "平板", 4799, discount=300,
        brand="Apple", stock=440, tags=["学习", "办公"], sales=5400, rating=4.7, review_count=7420,
        image_url=f"{_IMG}/P011.jpg",
        image_urls=[f"{_IMG}/P011.jpg", f"{_IMG}/P011_1.jpg", f"{_IMG}/P011_2.jpg"],
        specs={"storage": "128GB", "screen": "11″ Liquid Retina", "chip": "M3"},
    ),
    _make_product(
        "P012", "小米平板 7 Pro", "平板", 2499, discount=200,
        brand="小米", stock=620, tags=["娱乐", "性价比"], sales=6700, rating=4.5, review_count=6650,
        image_url=f"{_IMG}/P012.jpg",
        image_urls=[f"{_IMG}/P012.jpg", f"{_IMG}/P012_1.jpg", f"{_IMG}/P012_2.jpg"],
        specs={"storage": "256GB", "screen": "12.4″ 3K", "chip": "骁龙 8 Gen 2"},
    ),
    _make_product(
        "P013", "Galaxy Tab S10", "平板", 5499, discount=400,
        brand="Samsung", stock=240, tags=["旗舰", "办公"], sales=3600, rating=4.4, review_count=3020,
        image_url=f"{_IMG}/P013.jpg",
        specs={"storage": "256GB", "screen": "11″ Dynamic AMOLED", "stylus": "S Pen 内置"},
    ),

    # ═══ 笔记本 3 款 ═══
    _make_product(
        "P021", "MacBook Air M4", "笔记本", 9999, discount=800,
        brand="Apple", stock=140, tags=["轻薄", "办公", "新品"], sales=5100, rating=4.8, review_count=6890,
        image_url=f"{_IMG}/P021.jpg",
        specs={"memory": "16GB", "storage": "512GB", "screen": "15.3″ Liquid Retina"},
    ),
    _make_product(
        "P022", "Dell XPS 14", "笔记本", 10999, discount=900,
        brand="Dell", stock=120, tags=["旗舰", "办公"], sales=3200, rating=4.6, review_count=3500,
        image_url=f"{_IMG}/P022.jpg",
        specs={"memory": "32GB", "storage": "1TB", "screen": "14.5″ OLED"},
    ),
    _make_product(
        "P023", "联想拯救者 Y9000P", "笔记本", 8999, discount=700,
        brand="联想", stock=210, tags=["游戏", "高性能"], sales=4300, rating=4.5, review_count=4120,
        image_url=f"{_IMG}/P023.jpg",
        specs={"memory": "16GB", "storage": "1TB", "gpu": "RTX 4060"},
    ),

    # ═══ 配件 3 款 ═══
    _make_product(
        "P019", "罗技 MX Master 3S", "配件", 749, discount=100,
        brand="Logitech", stock=520, tags=["无线", "办公"], sales=4800, rating=4.8, review_count=6340,
        image_url=f"{_IMG}/P019.jpg",
        specs={"type": "无线鼠标", "dpi": "8000", "battery": "70天"},
    ),
    _make_product(
        "P016", "Anker 140W 充电器", "配件", 399, discount=60,
        brand="Anker", stock=2100, tags=["快充", "便携"], sales=12000, rating=4.8, review_count=15600,
        image_url=f"{_IMG}/P016.jpg",
        specs={"power": "140W", "ports": "3×USB-C + 1×USB-A", "protocol": "PD 3.1"},
    ),
    _make_product(
        "P020", "Keychron K3 Pro", "配件", 699, discount=80,
        brand="Keychron", stock=380, tags=["机械", "办公"], sales=2900, rating=4.4, review_count=2480,
        image_url=f"{_IMG}/P020.jpg",
        specs={"switch": "红轴", "layout": "75%", "connection": "蓝牙/有线"},
    ),

    # ═══ 显示器 3 款 ═══
    _make_product(
        "P026", "戴尔 U2724D", "显示器", 3299, discount=300,
        brand="Dell", stock=70, tags=["4K", "办公"], sales=2200, rating=4.6, review_count=1550,
        image_url=f"{_IMG}/P026.jpg",
        specs={"size": "27″", "resolution": "4K", "panel": "IPS Black"},
    ),
    _make_product(
        "P027", "LG 27GP850", "显示器", 2399, discount=200,
        brand="LG", stock=110, tags=["电竞", "高刷"], sales=3600, rating=4.5, review_count=2860,
        image_url=f"{_IMG}/P027.jpg",
        specs={"size": "27″", "resolution": "2K", "refresh": "165Hz"},
    ),
    _make_product(
        "P029", "华为 MateView SE", "显示器", 1399, discount=150,
        brand="华为", stock=190, tags=["护眼", "办公"], sales=3200, rating=4.3, review_count=1880,
        image_url=f"{_IMG}/P029.jpg",
        specs={"size": "23.8″", "resolution": "1080p", "panel": "IPS"},
    ),

    # ═══ 穿戴 2 款 ═══
    _make_product(
        "P036", "Apple Watch Ultra 3", "穿戴", 5999, discount=500,
        brand="Apple", stock=210, tags=["运动", "健康"], sales=4100, rating=4.7, review_count=5200,
        image_url=f"{_IMG}/P036.jpg",
        specs={"size": "49mm", "battery": "36h", "waterproof": "100m"},
    ),
    _make_product(
        "P037", "华为 Watch GT 6", "穿戴", 1999, discount=200,
        brand="华为", stock=340, tags=["健康", "续航"], sales=4700, rating=4.5, review_count=3920,
        image_url=f"{_IMG}/P037.jpg",
        specs={"size": "46mm", "battery": "14天", "sensors": "心率/血氧/体温"},
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
