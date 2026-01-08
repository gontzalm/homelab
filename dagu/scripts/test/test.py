import httpx

r = httpx.get("https://google.com")
print(f"Status code: {r.status_code}")
