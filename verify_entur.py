import asyncio
import os

from playwright.async_api import async_playwright


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--disable-web-security'])
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        file_path = f"file://{os.path.abspath('entur_siri_lite.html')}"
        print(f"Loading: {file_path}")

        await page.goto(file_path)

        # Wait for data to load
        print("Waiting for vehicle data...")
        await asyncio.sleep(5) # Wait for fetch

        # Take a screenshot
        await page.screenshot(path='entur_siri_lite_verify.png')
        print("Screenshot saved to entur_siri_lite_verify.png")

        # Try to hover/click something
        # We don't know the exact coordinates of a vehicle, but we can try to click
        # the center
        await page.mouse.click(640, 360)
        await asyncio.sleep(1)
        await page.screenshot(path='entur_siri_lite_click.png')

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
