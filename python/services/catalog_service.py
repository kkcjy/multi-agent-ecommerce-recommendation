"""Catalog data service for UI-friendly endpoints."""

from __future__ import annotations

from typing import Any, Iterable

from models.schemas import InventoryStatus, Product
from repositories.product_repository import ProductRepository

CATEGORY_EMOJI = {
    "手机": "📱",
    "平板": "💻",
    "耳机": "🎧",
    "配件": "🔌",
    "笔记本": "💻",
    "显示器": "🖥",
    "存储": "💾",
    "穿戴": "⌚",
    "无人机": "🛸",
    "游戏机": "🎮",
}

HOT_SEARCHES = [
    {"term": "iPhone", "emoji": "📱", "score": 98},
    {"term": "耳机", "emoji": "🎧", "score": 92},
    {"term": "平板", "emoji": "💻", "score": 88},
    {"term": "充电器", "emoji": "🔌", "score": 86},
    {"term": "游戏", "emoji": "🎮", "score": 84},
    {"term": "性价比", "emoji": "💰", "score": 82},
]


class CatalogService:
    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    async def list_categories(self) -> list[dict[str, Any]]:
        products = await self._repo.get_all_products(limit=1000)
        counts: dict[str, int] = {}
        for product in products:
            counts[product.category] = counts.get(product.category, 0) + 1
        items = [
            {
                "id": category,
                "name": category,
                "count": count,
                "emoji": CATEGORY_EMOJI.get(category, "📦"),
            }
            for category, count in counts.items()
        ]
        items.sort(key=lambda item: (-item["count"], item["name"]))
        return items

    async def search_products(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        brand: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> tuple[list[Product], int]:
        products = await self._repo.get_all_products(limit=1000)
        filtered = self._filter_products(
            products,
            query=query,
            category=category,
            tag=tag,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
        )
        sorted_products = self._sort_products(filtered, sort)
        return self._paginate(sorted_products, page, page_size)

    async def category_products(
        self,
        category: str,
        page: int,
        page_size: int,
        sort: str | None = None,
        tag: str | None = None,
        brand: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> tuple[list[Product], int]:
        category_value = category if category and category != "all" else ""
        return await self.search_products(
            query="",
            page=page,
            page_size=page_size,
            sort=sort,
            category=category_value or None,
            tag=tag,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
        )

    async def get_segment_products(
        self,
        segment: str,
        page: int,
        page_size: int,
        *,
        recent_views: list[str] | None = None,
        preferred_categories: list[str] | None = None,
    ) -> tuple[list[Product], int]:
        products = await self._repo.get_all_products(limit=1000)
        segment_key = (segment or "").lower()
        if segment_key == "hot":
            sorted_products = self._sort_products(products, "sales")
        elif segment_key == "new":
            sorted_products = [p for p in products if "新品" in (p.tags or [])]
            sorted_products = self._sort_products(sorted_products, "new")
        elif segment_key == "intent":
            categories = self._normalize_list(recent_views)
            sorted_products = self._filter_by_categories(products, categories)
            if not sorted_products:
                sorted_products = self._sort_products(products, "sales")
        elif segment_key == "personal":
            categories = self._normalize_list(preferred_categories) or self._normalize_list(recent_views)
            sorted_products = self._filter_by_categories(products, categories)
            if not sorted_products:
                sorted_products = self._sort_products(products, "sales")
        else:
            sorted_products = self._sort_products(products, "sales")

        return self._paginate(sorted_products, page, page_size)

    async def get_product(self, product_id: str) -> Product | None:
        items = await self._repo.get_by_ids([product_id])
        return items[0] if items else None

    async def get_related_products(self, product_id: str, limit: int = 6) -> list[Product]:
        products = await self._repo.get_all_products(limit=1000)
        target = next((p for p in products if p.product_id == product_id), None)
        if not target:
            return []

        def score(candidate: Product) -> tuple[int, int, int]:
            same_category = 1 if candidate.category == target.category else 0
            shared_tags = len(set(candidate.tags or []) & set(target.tags or []))
            same_brand = 1 if candidate.brand and candidate.brand == target.brand else 0
            return (same_category, shared_tags, same_brand)

        related = [p for p in products if p.product_id != product_id]
        related.sort(key=score, reverse=True)
        return related[:limit]

    def get_hot_searches(self) -> list[dict[str, Any]]:
        return list(HOT_SEARCHES)

    async def get_search_suggestions(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        products = await self._repo.get_all_products(limit=1000)
        suggestions: list[dict[str, Any]] = []
        seen: set[str] = set()
        for product in products:
            if q in product.name.lower() or q in product.category.lower() or q in (product.brand or "").lower():
                if product.name in seen:
                    continue
                seen.add(product.name)
                suggestions.append({
                    "text": product.name,
                    "product_id": product.product_id,
                    "category": product.category,
                    "emoji": CATEGORY_EMOJI.get(product.category, "📦"),
                })
            if len(suggestions) >= limit:
                break
        return suggestions

    def serialize_product(self, product: Product) -> dict[str, Any]:
        data = product.model_dump()
        price = float(data.get("price") or 0)
        discount = float(data.get("discount") or 0)
        final_price = data.get("final_price")
        if final_price is None:
            final_price = max(0.0, price - discount)
        original_price = data.get("original_price")
        if original_price is None:
            original_price = price
        data["price"] = price
        data["discount"] = discount
        data["final_price"] = float(final_price)
        data["original_price"] = float(original_price)

        status = data.get("inventory_status")
        if isinstance(status, InventoryStatus):
            status = status.value
        if not status:
            status = self._derive_inventory_status(data.get("stock", 0))
        data["inventory_status"] = status

        tags = data.get("tags") or []
        price_tags = data.get("price_tags") or self._derive_price_tags(tags, final_price, discount, status)
        data["price_tags"] = price_tags
        badges = data.get("badges") or self._derive_badges(tags, data.get("sales", 0), status)
        data["badges"] = badges

        data["image_urls"] = data.get("image_urls") or []
        data["external_url"] = data.get("external_url") or ""
        data["specs"] = data.get("specs") or {}
        return data

    def _filter_products(
        self,
        products: Iterable[Product],
        *,
        query: str,
        category: str | None,
        tag: str | None,
        brand: str | None,
        min_price: float | None,
        max_price: float | None,
    ) -> list[Product]:
        q = (query or "").strip().lower()
        results: list[Product] = []
        for product in products:
            if category and product.category != category:
                continue
            if tag and tag not in (product.tags or []):
                continue
            if brand and product.brand.lower() != brand.lower():
                continue
            price = product.final_price if product.final_price is not None else product.price
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            if q:
                if q not in product.name.lower() and q not in product.category.lower() and q not in (product.brand or "").lower():
                    tag_hit = any(q in t.lower() for t in (product.tags or []))
                    if not tag_hit:
                        continue
            results.append(product)
        return results

    def _filter_by_categories(self, products: Iterable[Product], categories: list[str]) -> list[Product]:
        if not categories:
            return []
        results = []
        for product in products:
            if product.category in categories:
                results.append(product)
        return results

    def _sort_products(self, products: list[Product], sort: str | None) -> list[Product]:
        key = (sort or "").lower()
        if key in ("price", "price_asc", "price-asc"):
            return sorted(products, key=self._price_value)
        if key in ("price_desc", "price-desc"):
            return sorted(products, key=self._price_value, reverse=True)
        if key in ("sales", "hot"):
            return sorted(products, key=lambda p: (p.sales, p.rating), reverse=True)
        if key == "rating":
            return sorted(products, key=lambda p: (p.rating, p.review_count), reverse=True)
        if key == "new":
            return sorted(products, key=lambda p: ("新品" in (p.tags or []), p.sales), reverse=True)
        if key in ("stock", "inventory"):
            return sorted(products, key=lambda p: p.stock, reverse=True)
        return sorted(products, key=lambda p: (p.sales, p.rating), reverse=True)

    def _paginate(self, products: list[Product], page: int, page_size: int) -> tuple[list[Product], int]:
        total = len(products)
        page = max(1, int(page))
        page_size = max(1, int(page_size))
        start = (page - 1) * page_size
        end = start + page_size
        return products[start:end], total

    def _price_value(self, product: Product) -> float:
        if product.final_price is not None:
            return product.final_price
        return product.price

    def _normalize_list(self, values: list[str] | None) -> list[str]:
        if not values:
            return []
        return [str(v).strip() for v in values if str(v).strip()]

    def _derive_inventory_status(self, stock: int) -> str:
        if stock <= 0:
            return InventoryStatus.OUT_OF_STOCK.value
        if stock <= 60:
            return InventoryStatus.LOW_STOCK.value
        return InventoryStatus.IN_STOCK.value

    def _derive_price_tags(self, tags: list[str], final_price: float, discount: float, status: str) -> list[str]:
        output: list[str] = []
        if discount > 0:
            output.append("discount")
        if final_price <= 199:
            output.append("value")
        if "新品" in tags:
            output.append("new")
        if status == InventoryStatus.LOW_STOCK.value:
            output.append("low_stock")
        return output

    def _derive_badges(self, tags: list[str], sales: int, status: str) -> list[str]:
        output: list[str] = []
        if "新品" in tags:
            output.append("new")
        if "旗舰" in tags:
            output.append("flagship")
        if sales >= 6000:
            output.append("hot")
        if status == InventoryStatus.LOW_STOCK.value:
            output.append("low_stock")
        return output
