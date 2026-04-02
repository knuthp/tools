/* global map */
(function() {
    function getMapData() {
        let extent, zoom, token, layerUrl;

        // Try to find the map object and its state
        if (typeof map !== 'undefined') {
            // Check for Leaflet
            if (map.getBounds && typeof map.getBounds === 'function') {
                const bounds = map.getBounds();
                extent = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()];
                zoom = Math.round(map.getZoom());
                console.log("Detected Leaflet");
            }
            // Check for OpenLayers (assuming global 'map' is OL map)
            else if (map.getView && typeof map.getView === 'function') {
                const view = map.getView();
                // Extent in projection coordinates
                const ext = view.calculateExtent(map.getSize());
                const proj = view.getProjection().getCode();
                // We'll need to transform this if not EPSG:4326
                // But let's just use what's there for now and let the python script handle it
                extent = ext;
                zoom = Math.round(view.getZoom());
                console.log("Detected OpenLayers, projection:", proj);
            }
            // Check for ArcGIS API for JS (commonly used in Norway)
            else if (map.extent) {
                const ext = map.extent;
                extent = [ext.xmin, ext.ymin, ext.xmax, ext.ymax];
                zoom = map.getZoom ? map.getZoom() : (map.getLOD ? map.getLOD().level : null);
                console.log("Detected ArcGIS API");
            }
        }

        // Fallback: search for the token in network requests
        const entries = performance.getEntriesByType('resource');
        const tileEntry = entries.find(e => e.name.includes('tilecache.norgeibilder.no') && e.name.includes('token='));

        if (tileEntry) {
            const url = new URL(tileEntry.name);
            token = url.searchParams.get('token');
            // Extract the base URL for the WMTS service
            // e.g. https://tilecache.norgeibilder.no/wmts/webmercator
            layerUrl = url.origin + url.pathname.split('?')[0];
            console.log("Found token in resource:", token);
        }

        return { extent, zoom, token, layerUrl };
    }

    const data = getMapData();
    if (!data.token) {
        alert("Could not find Norge i Bilder token. Make sure the map is loaded and showing imagery.");
        return;
    }

    const config = {
        token: data.token,
        extent: data.extent,
        zoom: data.zoom,
        layerUrl: data.layerUrl || "https://tilecache.norgeibilder.no/wmts/webmercator",
        maxZoom: 18,
        sourceUrl: window.location.href,
        timestamp: new Date().toISOString()
    };

    const json = JSON.stringify(config, null, 2);

    const div = document.createElement('div');
    div.style.position = 'fixed';
    div.style.top = '10px';
    div.style.left = '10px';
    div.style.zIndex = '10000';
    div.style.backgroundColor = 'white';
    div.style.padding = '20px';
    div.style.border = '2px solid black';
    div.style.boxShadow = '5px 5px 15px rgba(0,0,0,0.5)';
    div.style.maxWidth = '80%';
    div.style.maxHeight = '90%';
    div.style.overflow = 'auto';
    div.style.color = 'black';
    div.style.fontFamily = 'sans-serif';

    div.innerHTML = `
        <h3 style="margin-top:0">Norge i Bilder Export</h3>
        <p>Copy this JSON configuration and save it as <code>config.json</code> to use with the Python script:</p>
        <textarea id="nib-config" style="width:100%; height:150px; font-family:monospace; margin-bottom:10px;">${json}</textarea>
        <br>
        <button id="copy-btn" style="padding:10px; cursor:pointer;">Copy to Clipboard</button>
        <button id="close-btn" style="padding:10px; cursor:pointer; margin-left:10px;">Close</button>
    `;

    document.body.appendChild(div);

    document.getElementById('copy-btn').onclick = function() {
        document.getElementById('nib-config').select();
        document.execCommand('copy');
        this.textContent = 'Copied!';
        setTimeout(() => this.textContent = 'Copy to Clipboard', 2000);
    };

    document.getElementById('close-btn').onclick = function() {
        div.remove();
    };
})();
