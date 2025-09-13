from events import ee

@ee.on("test")
async def test_event():
    print("test event")