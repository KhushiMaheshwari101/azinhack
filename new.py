import time
from tinyfish import TinyFish

client = TinyFish()

URLS = [ # 1) Indian electronics store ka koi component ya product listing page
    "https://careers.swiggy.in/",     # 2) kisi company ka careers page, jo bina login ke khulta ho
    "https://erera.co.in/ereradelhi/projects/registered-projects",  # 3) Delhi RERA, dobara dekhne ke liye
    "https://scrapeme.live/shop",    # 4) control, ye pehle chala tha
]

GOAL = "Extract the page title and the first visible heading. Return JSON."
TIME_LIMIT = 60

for url in URLS:
    t0 = time.time()
    status = "no result"
    result = None
    try:
        with client.agent.stream(url=url, goal=GOAL) as stream:
            for event in stream:
                if time.time() - t0 > TIME_LIMIT:
                    status = "TIMEOUT"
                    break
                if "HEARTBEAT" in str(event.type):
                    continue
                if "COMPLETE" in str(event.type):
                    status = "COMPLETE"
                    result = getattr(event, "result", None)
                    break
    except Exception as e:
        status = "ERROR: " + str(e)[:150]
    print(url, "->", status, round(time.time() - t0, 1), "sec")
    print("   result:", result)