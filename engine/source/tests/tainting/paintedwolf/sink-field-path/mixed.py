# ruleid: flow
sink({"items": [{"url": source()}]})
sink({"items": [{"url": "https://example.com/", "body": source()}]})
sink({"items": [{"url": "https://example.com/"}, {"url": source()}]})
