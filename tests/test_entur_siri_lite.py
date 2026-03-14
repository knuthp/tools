import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module", autouse=True)
def setup_server():
    import subprocess
    import time
    process = subprocess.Popen(["python3", "-m", "http.server", "8000"])
    time.sleep(2)  # Give it a second to start
    yield
    process.terminate()


def test_map_loads_and_fetches_data(page: Page):
    # Go to the local server
    page.goto("http://localhost:8000/entur_siri_lite.html")

    # Check title
    expect(page).to_have_title("Entur SIRI-Lite Real-Time Map")

    # Check if map container exists
    map_container = page.locator("#map")
    expect(map_container).to_be_visible()

    # Wait for the network request to Entur API
    # The API might be slow or down, so we set a reasonable timeout
    try:
        url_pattern = "**/realtime/v1/rest/vm?datasetId=RUT"
        with page.expect_response(url_pattern, timeout=30000) as response_info:
            response = response_info.value
            assert response.status == 200
            json_data = response.json()
            assert "Siri" in json_data
    except Exception as e:
        pytest.fail(f"Failed to fetch data from Entur API: {e}")

    # Verify that deck.gl has initialized and created a canvas
    # There might be multiple canvases (one for MapLibre, one for Deck.gl)
    canvas = page.locator("canvas").first
    expect(canvas).to_be_visible()

    # Take a screenshot for visual verification
    page.screenshot(path="screenshot_entur_siri_lite.png")
