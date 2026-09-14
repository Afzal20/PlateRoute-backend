#!/usr/bin/env python3
"""
Scrape 200 authentic food recipes with instructions, ingredients,
and download 1 primary image + 3 extra images per recipe (total 800 images).
Generates formatted dataset at backend/data/foods_200.json.
"""

import concurrent.futures
import json
import os
import re
import string
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_FOODS_DIR = BASE_DIR / "media" / "foods"
DATA_FILE = BASE_DIR / "data" / "foods_200.json"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0 PlateRouteBot/1.0"
})


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "_", text).strip("_")


def calculate_price_minor(category: str) -> int:
    category_prices = {
        "beef": 42000,
        "lamb": 48000,
        "goat": 46000,
        "seafood": 45000,
        "chicken": 32000,
        "pork": 34000,
        "pasta": 28000,
        "vegetarian": 22000,
        "vegan": 21000,
        "breakfast": 18000,
        "starter": 16000,
        "side": 12000,
        "dessert": 19000,
        "miscellaneous": 25000,
    }
    base = category_prices.get(category.lower(), 25000)
    import hashlib
    offset = (int(hashlib.md5(category.encode()).hexdigest(), 16) % 15) * 1000
    return base + offset


def fetch_200_recipes() -> list:
    print("Fetching 200 recipes from TheMealDB...")
    meals = []
    seen_names = set()

    for char in string.ascii_lowercase:
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?f={char}"
        try:
            resp = SESSION.get(url, timeout=10)
            data = resp.json()
            raw_meals = data.get("meals") or []
            for m in raw_meals:
                name = m.get("strMeal", "").strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                meals.append(m)
                if len(meals) >= 200:
                    break
        except Exception as err:
            print(f"Error fetching letter {char}: {err}")

        if len(meals) >= 200:
            break

    print(f"Retrieved {len(meals)} unique recipes.")
    return meals[:200]


def parse_ingredients(meal: dict) -> list:
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        meas = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            ingredients.append({
                "ingredient": ing.strip(),
                "measure": (meas or "").strip()
            })
    return ingredients


def query_wikimedia_images(query: str, count: int = 5) -> list:
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} food",
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 800,
        "format": "json",
        "gsrlimit": count
    }
    try:
        resp = SESSION.get(url, params=params, timeout=8)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        urls = []
        for p in pages.values():
            info = p.get("imageinfo", [{}])[0]
            thumb = info.get("thumburl") or info.get("url")
            if thumb and any(thumb.lower().endswith(ext) or ext in thumb.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                urls.append(thumb)
        return urls
    except Exception:
        return []


def get_3_extra_images(meal_name: str, category: str, primary_thumb: str) -> list:
    collected = []
    seen = {primary_thumb}

    # Query 1: Full dish name
    candidates = query_wikimedia_images(meal_name, 6)
    for c in candidates:
        if c not in seen:
            seen.add(c)
            collected.append(c)
            if len(collected) >= 3:
                return collected

    # Query 2: First 2-3 words of meal name
    words = meal_name.split()
    if len(words) > 2:
        short_name = " ".join(words[:2])
        candidates = query_wikimedia_images(short_name, 5)
        for c in candidates:
            if c not in seen:
                seen.add(c)
                collected.append(c)
                if len(collected) >= 3:
                    return collected

    # Query 3: Category + food
    candidates = query_wikimedia_images(f"{category} dish recipe", 8)
    for c in candidates:
        if c not in seen:
            seen.add(c)
            collected.append(c)
            if len(collected) >= 3:
                return collected

    # Fallback to high quality food stock images if still needed
    backup_urls = [
        f"https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&auto=format&fit=crop&q=80",
        f"https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&auto=format&fit=crop&q=80",
        f"https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&auto=format&fit=crop&q=80",
        f"https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&auto=format&fit=crop&q=80",
        f"https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&auto=format&fit=crop&q=80",
    ]
    for b in backup_urls:
        if b not in seen:
            seen.add(b)
            collected.append(b)
            if len(collected) >= 3:
                break

    return collected[:3]


def download_single_image(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        return True

    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, timeout=12, stream=True)
            if resp.status_code == 200:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                if dest_path.stat().st_size > 500:
                    return True
        except Exception:
            time.sleep(0.5)

    return False


def process_meal(item_index: int, raw_meal: dict) -> dict:
    name = (raw_meal.get("strMeal") or f"Special Dish {item_index}").strip()
    category = (raw_meal.get("strCategory") or "Miscellaneous").strip()
    area = (raw_meal.get("strArea") or "International").strip()
    instructions = (raw_meal.get("strInstructions") or "Prepared fresh with chef selection of authentic seasonings and ingredients.").strip()
    primary_thumb = (raw_meal.get("strMealThumb") or "").strip()
    if not primary_thumb:
        primary_thumb = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&auto=format&fit=crop&q=80"
    tags = [t.strip() for t in (raw_meal.get("strTags") or "").split(",") if t and t.strip()]

    slug = slugify(name)[:50]
    folder_name = f"item_{item_index:03d}_{slug}"
    item_media_dir = MEDIA_FOODS_DIR / folder_name
    item_media_dir.mkdir(parents=True, exist_ok=True)

    # Ingredients
    ingredients = parse_ingredients(raw_meal)

    # 3 Extra images
    extra_image_urls = get_3_extra_images(name, category, primary_thumb)
    while len(extra_image_urls) < 3:
        extra_image_urls.append(primary_thumb)

    # Download primary image
    main_file = item_media_dir / "main.jpg"
    download_single_image(primary_thumb, main_file)

    # Download extra images
    extra_files = []
    for idx, ext_url in enumerate(extra_image_urls[:3], start=1):
        target_file = item_media_dir / f"extra_{idx}.jpg"
        ok = download_single_image(ext_url, target_file)
        if not ok and main_file.exists():
            import shutil
            shutil.copy(main_file, target_file)
        extra_files.append(f"/media/foods/{folder_name}/extra_{idx}.jpg")

    # Short summary description
    ing_summary = ", ".join([i["ingredient"] for i in ingredients[:4]])
    desc_lines = []
    if area and area != "Unknown":
        desc_lines.append(f"Authentic {area}-style {category.lower()} dish.")
    if ing_summary:
        desc_lines.append(f"Crafted with fresh {ing_summary}.")
    if instructions:
        first_step = instructions.split(".")[0].strip()
        if len(first_step) > 20:
            desc_lines.append(first_step + ".")
    description = " ".join(desc_lines)

    price_minor = calculate_price_minor(category)

    # Option groups
    option_groups = [
        {
            "title": "Portion Size",
            "min_select": 1,
            "max_select": 1,
            "options": [
                {"label": "Regular", "price_delta_minor": 0, "is_default": True, "available": True},
                {"label": "Large (Extra portion)", "price_delta_minor": 12000, "is_default": False, "available": True},
                {"label": "Platter (Serves 2)", "price_delta_minor": 22000, "is_default": False, "available": True},
            ]
        },
        {
            "title": "Spice Level",
            "min_select": 0,
            "max_select": 1,
            "options": [
                {"label": "Mild", "price_delta_minor": 0, "is_default": True, "available": True},
                {"label": "Medium Spicy", "price_delta_minor": 0, "is_default": False, "available": True},
                {"label": "Extra Hot", "price_delta_minor": 2000, "is_default": False, "available": True},
            ]
        },
        {
            "title": "Special Add-ons",
            "min_select": 0,
            "max_select": 3,
            "options": [
                {"label": "Signature Dip / Sauce", "price_delta_minor": 3500, "is_default": False, "available": True},
                {"label": "Extra Cheese Melt", "price_delta_minor": 6000, "is_default": False, "available": True},
                {"label": "Chilled Beverage (330ml)", "price_delta_minor": 4500, "is_default": False, "available": True},
            ]
        }
    ]

    return {
        "index": item_index,
        "id_meal": raw_meal.get("idMeal", ""),
        "name": name,
        "slug": slug,
        "category": category,
        "cuisine": area,
        "tags": tags,
        "description": description,
        "instructions": instructions,
        "ingredients": ingredients,
        "base_price_minor": price_minor,
        "currency": "BDT",
        "image_url": f"/media/foods/{folder_name}/main.jpg",
        "extra_images": extra_files,
        "remote_primary_image": primary_thumb,
        "remote_extra_images": extra_image_urls[:3],
        "option_groups": option_groups,
    }


def main():
    MEDIA_FOODS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    recipes = fetch_200_recipes()
    if len(recipes) < 200:
        print(f"Warning: Only found {len(recipes)} recipes.")

    print(f"Starting concurrent download and processing for {len(recipes)} recipes...")
    start_time = time.time()

    processed_items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_idx = {
            executor.submit(process_meal, idx, meal): idx
            for idx, meal in enumerate(recipes, start=1)
        }
        completed = 0
        for future in concurrent.futures.as_completed(future_to_idx):
            completed += 1
            idx = future_to_idx[future]
            try:
                result = future.result()
                processed_items.append(result)
                if completed % 25 == 0 or completed == len(recipes):
                    print(f"Progress: {completed}/{len(recipes)} items processed.")
            except Exception as e:
                print(f"Item {idx} failed with error: {e}")

    # Sort by original index
    processed_items.sort(key=lambda x: x["index"])

    # Write formatted JSON
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(processed_items, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"Successfully processed and saved {len(processed_items)} items in {elapsed:.2f}s.")
    print(f"Dataset saved to: {DATA_FILE}")

    # Verify files on disk
    downloaded_images = list(MEDIA_FOODS_DIR.glob("*/*.jpg"))
    print(f"Total image files on disk in media/foods: {len(downloaded_images)}")


if __name__ == "__main__":
    main()
