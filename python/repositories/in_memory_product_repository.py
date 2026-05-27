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
    description: str = "",
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
        description=description,
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
        description="iPhone 16 Pro采用钛金属设计，搭载A18 Pro芯片，支持Dynamic Island。提供6.3英寸高分辨率显示屏，专业级摄像头系统支持长焦拍摄和高品质视频录制。IP69防护等级提供全面防护。续航能力强劲，全天候使用无压力。",
    ),
    _make_product(
        "P002", "华为 Mate 70", "手机", 5999, discount=300,
        brand="华为", stock=340, tags=["旗舰", "国产"], sales=7600, rating=4.7, review_count=12980,
        image_url=f"{_IMG}/P002.jpg",
        image_urls=[f"{_IMG}/P002.jpg", f"{_IMG}/P002_1.jpg", f"{_IMG}/P002_2.jpg"],
        specs={"storage": "256GB", "color": "雅黑", "chip": "麒麟 9100"},
        description="华为Mate 70国产旗舰手机，搭载麒麟9100处理器，支持鸿蒙系统。提供高效能电池和优秀的拍照能力，支持多倍光学变焦。支持快速充电和无线充电，续航表现出色。",
    ),
    _make_product(
        "P003", "小米 15", "手机", 3999, discount=200,
        brand="小米", stock=880, tags=["性价比", "新品"], sales=6800, rating=4.6, review_count=9040,
        image_url=f"{_IMG}/P003.jpg",
        image_urls=[f"{_IMG}/P003.jpg", f"{_IMG}/P003_1.jpg", f"{_IMG}/P003_2.jpg"],
        specs={"storage": "256GB", "color": "白色", "chip": "骁龙 8 Elite"},
        description="小米15是性价比之选，搭载骁龙8 Elite处理器，性能强劲。120Hz高刷屏提供流畅视觉体验，支持快速充电技术。续航能力强，拍照性能均衡，日常使用表现出色。",
    ),
    _make_product(
        "P004", "Samsung Galaxy S26", "手机", 6999, discount=400,
        brand="Samsung", stock=210, tags=["旗舰"], sales=5200, rating=4.5, review_count=6120,
        image_url=f"{_IMG}/P004.jpg",
        image_urls=[f"{_IMG}/P004.jpg", f"{_IMG}/P004_1.jpg", f"{_IMG}/P004_2.jpg"],
        specs={"storage": "256GB", "color": "钛灰", "chip": "Exynos 2500"},
        description="三星Galaxy S26旗舰型号，搭载Exynos 2500处理器，性能顶级。Dynamic AMOLED屏幕色彩还原准确，IP68防护等级提供全面防护。拍照和续航表现出色，支持多项Galaxy特色功能。",
    ),

    # ═══ 耳机 4 款 ═══
    _make_product(
        "P006", "AirPods Pro 3", "耳机", 1899, discount=150,
        brand="Apple", stock=1200, tags=["降噪", "无线", "新品"], sales=8600, rating=4.8, review_count=14220,
        image_url=f"{_IMG}/P006.jpg",
        image_urls=[f"{_IMG}/P006.jpg", f"{_IMG}/P006_1.jpg", f"{_IMG}/P006_2.jpg"],
        specs={"type": "入耳式", "battery": "6h+30h", "waterproof": "IP54"},
        description="AirPods Pro 3采用主动降噪技术，提供沉浸式听觉体验。透明模式让你融入周围环境，空间音频提供3D立体声效果。长达30小时的充电盒续航，防水防汗设计。与Apple设备无缝协作，是Apple用户的首选耳机。",
    ),
    _make_product(
        "P007", "Sony WH-1000XM6", "耳机", 2499, discount=280,
        brand="Sony", stock=260, tags=["头戴", "降噪"], sales=5200, rating=4.7, review_count=7040,
        image_url=f"{_IMG}/P007.jpg",
        image_urls=[f"{_IMG}/P007.jpg", f"{_IMG}/P007_1.jpg", f"{_IMG}/P007_2.jpg"],
        specs={"type": "头戴式", "battery": "40h", "noise_cancel": "双芯降噪"},
        description="Sony WH-1000XM6业界领先的降噪性能，双芯降噪技术效果显著。40小时超长续航，一周只需充电一次。触控操作便捷，快速充电功能强劲。舒适的贴耳设计适合长时间佩戴，音质纯净细腻。",
    ),
    _make_product(
        "P008", "Bose QC Ultra", "耳机", 2299, discount=200,
        brand="Bose", stock=180, tags=["降噪", "舒适"], sales=3900, rating=4.6, review_count=4550,
        image_url=f"{_IMG}/P008.jpg",
        image_urls=[f"{_IMG}/P008.jpg", f"{_IMG}/P008_1.jpg", f"{_IMG}/P008_2.jpg"],
        specs={"type": "头戴式", "battery": "24h", "noise_cancel": "自适应降噪"},
        description="Bose QC Ultra提供自适应降噪技术，声音质感沉浸式。24小时续航能力满足日常使用。舒适的耳垫设计适合长时间佩戴，不易疲劳。快速配对功能方便，与多种设备兼容。",
    ),
    _make_product(
        "P009", "Redmi Buds 6 Pro", "耳机", 399, discount=80,
        brand="Redmi", stock=1600, tags=["性价比", "降噪"], sales=9200, rating=4.5, review_count=11780,
        image_url=f"{_IMG}/P009.jpg",
        image_urls=[f"{_IMG}/P009.jpg", f"{_IMG}/P009_1.jpg", f"{_IMG}/P009_2.jpg"],
        specs={"type": "入耳式", "battery": "8h+30h", "waterproof": "IPX5"},
        description="Redmi Buds 6 Pro是性价比之选，双芯降噪技术效果出色。IPX5防水防汗，适合运动佩戴。8小时单次续航加30小时盒子续航，使用时间长。通话降噪功能突出，支持快速配对。",
    ),

    # ═══ 平板 3 款 ═══
    _make_product(
        "P011", "iPad Air M3", "平板", 4799, discount=300,
        brand="Apple", stock=440, tags=["学习", "办公"], sales=5400, rating=4.7, review_count=7420,
        image_url=f"{_IMG}/P011.jpg",
        image_urls=[f"{_IMG}/P011.jpg", f"{_IMG}/P011_1.jpg", f"{_IMG}/P011_2.jpg"],
        specs={"storage": "128GB", "screen": "11″ Liquid Retina", "chip": "M3"},
        description="iPad Air M3轻薄便携，M3芯片性能强劲，处理大型应用毫无压力。11英寸Liquid Retina屏幕色彩准确，适合创意工作。支持Apple Pencil提升创意创作能力。续航能力强，全天候使用无压力。",
    ),
    _make_product(
        "P012", "小米平板 7 Pro", "平板", 2499, discount=200,
        brand="小米", stock=620, tags=["娱乐", "性价比"], sales=6700, rating=4.5, review_count=6650,
        image_url=f"{_IMG}/P012.jpg",
        image_urls=[f"{_IMG}/P012.jpg", f"{_IMG}/P012_1.jpg", f"{_IMG}/P012_2.jpg"],
        specs={"storage": "256GB", "screen": "12.4″ 3K", "chip": "骁龙 8 Gen 2"},
        description="小米平板7 Pro大屏幕设计，12.4英寸3K分辨率，视觉效果震撼。骁龙8 Gen 2处理器性能强劲。120Hz刷新率提供流畅体验。续航时间长，适合娱乐和办公。256GB大存储满足内容存储需求。",
    ),
    _make_product(
        "P013", "Galaxy Tab S10", "平板", 5499, discount=400,
        brand="Samsung", stock=240, tags=["旗舰", "办公"], sales=3600, rating=4.4, review_count=3020,
        image_url=f"{_IMG}/P013.jpg",
        specs={"storage": "256GB", "screen": "11″ Dynamic AMOLED", "stylus": "S Pen 内置"},
        description="Galaxy Tab S10配备Dynamic AMOLED屏幕，色彩还原准确。内置S Pen提升创作和编辑能力。高刷新率屏幕提供流畅视觉体验。适合专业用户进行办公和创意设计工作。强大性能处理复杂任务毫无压力。",
    ),

    # ═══ 笔记本 3 款 ═══
    _make_product(
        "P021", "MacBook Air M4", "笔记本", 9999, discount=800,
        brand="Apple", stock=140, tags=["轻薄", "办公", "新品"], sales=5100, rating=4.8, review_count=6890,
        image_url=f"{_IMG}/P021.jpg",
        specs={"memory": "16GB", "storage": "512GB", "screen": "15.3″ Liquid Retina"},
        description="MacBook Air M4轻薄便携，M4芯片性能强劲，续航能力出色。15.3英寸Liquid Retina屏幕，色彩准确，视觉效果优秀。静音散热设计，办公体验安静舒适。16GB内存满足专业工作需求。",
    ),
    _make_product(
        "P022", "Dell XPS 14", "笔记本", 10999, discount=900,
        brand="Dell", stock=120, tags=["旗舰", "办公"], sales=3200, rating=4.6, review_count=3500,
        image_url=f"{_IMG}/P022.jpg",
        specs={"memory": "32GB", "storage": "1TB", "screen": "14.5″ OLED"},
        description="Dell XPS 14高端商务本，14.5英寸高分辨率OLED屏幕，色彩还原准确。32GB内存和1TB存储提供强大性能。轻薄设计便于携带，续航能力强。适合需要高性能的商务和专业工作。",
    ),
    _make_product(
        "P023", "联想拯救者 Y9000P", "笔记本", 8999, discount=700,
        brand="联想", stock=210, tags=["游戏", "高性能"], sales=4300, rating=4.5, review_count=4120,
        image_url=f"{_IMG}/P023.jpg",
        specs={"memory": "16GB", "storage": "1TB", "gpu": "RTX 4060"},
        description="联想拯救者Y9000P游戏本选择，配备RTX 4060显卡，游戏性能强劲。高刷新率屏幕提供流畅游戏体验。散热性能强，长时间游戏不会过热。16GB内存和1TB存储满足游戏需求。",
    ),

    # ═══ 配件 3 款 ═══
    _make_product(
        "P019", "罗技 MX Master 3S", "配件", 749, discount=100,
        brand="Logitech", stock=520, tags=["无线", "办公"], sales=4800, rating=4.8, review_count=6340,
        image_url=f"{_IMG}/P019.jpg",
        specs={"type": "无线鼠标", "dpi": "8000", "battery": "70天"},
        description="罗技MX Master 3S专业级无线鼠标，8000 DPI精准追踪。可定制按键提升工作效率。与多设备兼容，支持无缝切换。70天超长续航，电池耐用。人体工学设计，长时间使用舒适。",
    ),
    _make_product(
        "P016", "Anker 140W 充电器", "配件", 399, discount=60,
        brand="Anker", stock=2100, tags=["快充", "便携"], sales=12000, rating=4.8, review_count=15600,
        image_url=f"{_IMG}/P016.jpg",
        specs={"power": "140W", "ports": "3×USB-C + 1×USB-A", "protocol": "PD 3.1"},
        description="Anker 140W充电器提供超快速充电能力，支持PD 3.1协议。3个USB-C和1个USB-A接口，支持多设备同时充电。紧凑便携设计，易于携带。兼容性强，支持各种设备充电。",
    ),
    _make_product(
        "P020", "Keychron K3 Pro", "配件", 699, discount=80,
        brand="Keychron", stock=380, tags=["机械", "办公"], sales=2900, rating=4.4, review_count=2480,
        image_url=f"{_IMG}/P020.jpg",
        specs={"switch": "红轴", "layout": "75%", "connection": "蓝牙/有线"},
        description="Keychron K3 Pro机械键盘，75%紧凑型设计节省空间。红轴手感轻快，适合长时间打字。蓝牙和有线双连接方式灵活使用。支持多设备配对。适合办公和编程工作。",
    ),

    # ═══ 显示器 3 款 ═══
    _make_product(
        "P026", "戴尔 U2724D", "显示器", 3299, discount=300,
        brand="Dell", stock=70, tags=["4K", "办公"], sales=2200, rating=4.6, review_count=1550,
        image_url=f"{_IMG}/P026.jpg",
        specs={"size": "27″", "resolution": "4K", "panel": "IPS Black"},
        description="戴尔U2724D 4K分辨率显示器，27英寸大屏幕。IPS Black面板色彩准确，黑色还原深邃。适合专业设计和视频编辑工作。3年保修服务提供安心保障。色彩准确度高，是专业工作者的首选。",
    ),
    _make_product(
        "P027", "LG 27GP850", "显示器", 2399, discount=200,
        brand="LG", stock=110, tags=["电竞", "高刷"], sales=3600, rating=4.5, review_count=2860,
        image_url=f"{_IMG}/P027.jpg",
        specs={"size": "27″", "resolution": "2K", "refresh": "165Hz"},
        description="LG 27GP850电竞显示器，2K分辨率，27英寸大屏幕。165Hz超高刷新率，响应速度极快。适合高竞技游戏，提供流畅游戏体验。色彩还原准确，也适合设计和内容创作。",
    ),
    _make_product(
        "P029", "华为 MateView SE", "显示器", 1399, discount=150,
        brand="华为", stock=190, tags=["护眼", "办公"], sales=3200, rating=4.3, review_count=1880,
        image_url=f"{_IMG}/P029.jpg",
        specs={"size": "23.8″", "resolution": "1080p", "panel": "IPS"},
        description="华为MateView SE护眼显示器，1080p分辨率，23.8英寸大小。IPS面板色彩准确，蓝光护眼技术保护眼睛。适合长时间办公和日常使用。价格亲民，功能齐全。",
    ),

    # ═══ 穿戴 2 款 ═══
    _make_product(
        "P036", "Apple Watch Ultra 3", "穿戴", 5999, discount=500,
        brand="Apple", stock=210, tags=["运动", "健康"], sales=4100, rating=4.7, review_count=5200,
        image_url=f"{_IMG}/P036.jpg",
        specs={"size": "49mm", "battery": "36h", "waterproof": "100m"},
        description="Apple Watch Ultra 3户外运动必备，49mm大屏幕显示清晰。续航能力36小时，一周只需充电一次。100m防水防护，适合水下运动。运动追踪准确，健康监测功能全面。",
    ),
    _make_product(
        "P037", "华为 Watch GT 6", "穿戴", 1999, discount=200,
        brand="华为", stock=340, tags=["健康", "续航"], sales=4700, rating=4.5, review_count=3920,
        image_url=f"{_IMG}/P037.jpg",
        specs={"size": "46mm", "battery": "14天", "sensors": "心率/血氧/体温"},
        description="华为Watch GT 6健康监测专家，14天超长续航，续航能力业界领先。心率血氧体温监测，睡眠分析功能详细。运动追踪准确，支持100+运动类型。46mm表盘大屏显示，操作便利。",
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
