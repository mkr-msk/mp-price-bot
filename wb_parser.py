import aiohttp
from gsheets import append, get_all_wb_articles

async def fetch_price_for(articul: str):
    url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&nm={articul}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as response:
            data = await response.json()
            price = data["data"]["products"][0]["salePriceU"] / 100
            append(source="wb", product=articul, text=str(price))
            print(f"✅ {articul} = {price}₽")

async def fetch_price():
    articles = get_all_wb_articles()
    for article in articles:
        try:
            await fetch_price_for(article)
        except Exception as e:
            print(f"⚠️ {article} — ошибка: {e}")
