import aiohttp, bs4, re
from gsheets import append

URL = "https://www.ozon.ru/product/ritter-svetilnik-potolochnyy-vstraivaemyy-arton-chernyy-59951-7-567765492"          # ссылка на товар

PRICE_RE = re.compile(r'"price":"(\d+)"')              # в исходнике есть JSON

async def fetch_ozon():
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as s:
        html = await (await s.get(URL, timeout=10)).text()
    price = int(PRICE_RE.search(html).group(1))
    append("ozon",
           product="ritter-svetilnik-potolochnyy-vstraivaemyy-arton-chernyy-59951-7-567765492",
           text=str(price/100))
