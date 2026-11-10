#!/usr/bin/env python3
"""สร้าง anime_db.json จากเว็บจริง (รันบนมือถือ/คอมของคุณ)
Termux:  pkg install python -y && pip install requests beautifulsoup4
รัน:     python scrape.py            (ได้ไฟล์ anime_db.json ในโฟลเดอร์เดียวกัน)
ทดสอบเร็ว: python scrape.py 2       (ดึงแค่ 2 หน้าต่อหมวด)
"""
import json, re, sys, time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

MAX_PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 60
H = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"}

A = "https://animeruka.com/catalog/"
F = "https://fairyanime.net/category/"
SUB, DUB = "%e0%b8%8b%e0%b8%b1%e0%b8%9a%e0%b9%84%e0%b8%97%e0%b8%a2/", "%e0%b8%9e%e0%b8%b2%e0%b8%81%e0%b8%a2%e0%b9%8c%e0%b9%84%e0%b8%97%e0%b8%a2/"
FSUB = "%E0%B8%8B%E0%B8%B1%E0%B8%9A%E0%B9%84%E0%B8%97%E0%B8%A2/"
FDUB = "%E0%B8%9E%E0%B8%B2%E0%B8%81%E0%B8%A2%E0%B9%8C%E0%B9%84%E0%B8%97%E0%B8%A2/"

# (source, ชื่อโชว์, type, ป้าย, สีป้าย, url หมวด)
JOBS = [
 ("animeruka","Animeruka","sub","ซับไทย","bg-purple-600",A+SUB),
 ("animeruka","Animeruka","dub","พากย์ไทย","bg-blue-600",A+DUB),
 ("fairyanime","Fairyanime","sub","ซับไทย","bg-purple-600",F+FSUB),
 ("fairyanime","Fairyanime","dub","พากย์ไทย","bg-blue-600",F+FDUB),
 ("anifume","Anifume","sub","ซับไทย","bg-purple-600","https://anifume.com/"),
 ("alpha-hen","Alpha-hen","sub","ซับไทย","bg-purple-600","https://www.alpha-hen.com/"),
]
# หมายเหตุ: เดอะมูฟวี่ของ Animeruka ใช้ลิงก์เดียวกับพากย์ไทย จึงไม่ดึงซ้ำ
# ถ้ามีลิงก์หมวดหนังจริง เพิ่มบรรทัดเป็น type "movie" ได้

def img_src(img):
    for k in ("data-src","data-lazy-src","data-original","src"):
        v = img.get(k)
        if v and not v.startswith("data:"): return v
    ss = img.get("srcset") or img.get("data-srcset")
    return ss.split()[0] if ss else ""

def parse(html, base):
    """หาการ์ด = ลิงก์ที่มีรูป; ชื่อจาก title/alt/ข้อความ"""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base).netloc
    out = []
    for a in soup.find_all("a", href=True):
        img = a.find("img")
        if not img: continue
        href = urljoin(base, a["href"])
        if urlparse(href).netloc != host: continue
        if re.search(r"/(category|catalog|page|tag|genre)/|#", href) and not re.search(r"/(anime|series|movie|watch|video)", href):
            if href.rstrip("/") == base.rstrip("/"): continue
        title = (a.get("title") or img.get("alt") or "").strip()
        if not title:
            card = a.find_parent(["article","div","li"]) or a
            h = card.find(["h1","h2","h3","h4"])
            title = (h.get_text(" ", strip=True) if h else a.get_text(" ", strip=True))
        title = re.sub(r"\s+", " ", title).strip()
        thumb = urljoin(base, img_src(img))
        if title and thumb: out.append((title, href, thumb))
    return out, soup

def next_url(soup, base, page):
    n = soup.find("a", rel=lambda r: r and "next" in r) or soup.select_one("a.next, a.next.page-numbers")
    if n and n.get("href"): return urljoin(base, n["href"])
    return None

def crawl(url):
    seen, items, cur, page = set(), [], url, 1
    while cur and page <= MAX_PAGES:
        try:
            r = requests.get(cur, headers=H, timeout=30); r.raise_for_status()
        except Exception as e:
            print("  ! ", cur, e); break
        got, soup = parse(r.text, cur)
        new = [g for g in got if g[1] not in seen]
        for g in new: seen.add(g[1])
        items += new
        print(f"  หน้า {page}: +{len(new)} (รวม {len(items)})")
        if not new: break
        nxt = next_url(soup, cur, page)
        if not nxt:  # เดา /page/N/
            page_try = url.rstrip("/") + f"/page/{page+1}/"
            nxt = page_try if page < MAX_PAGES else None
        cur, page = nxt, page + 1
        time.sleep(0.5)
    return items

db = []
for src, name, typ, badge, color, url in JOBS:
    print(f"[{name} / {badge}] {url}")
    for i, (t, link, th) in enumerate(crawl(url), 1):
        db.append({"id": f"{src}-{typ}-{i}", "title": t, "subTitle": f"แหล่งที่มา: {name}",
                   "badge": badge, "badgeColor": color, "type": typ, "source": src,
                   "thumb": th, "mainUrl": link})
json.dump(db, open("anime_db.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("เสร็จ:", len(db), "เรื่อง -> anime_db.json")
