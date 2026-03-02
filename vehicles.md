# Prompts


```
I want a deck gl frontend that queries

https://maps.sporet.no/arcgis/rest/services/Proxy/Sporet/FeatureServer/2/query?f=json&outSr=4326
periodically and updates a map with the vehicles

Json looks like this

{
    "objectIdFieldName": "vehicleid",
    "displayFieldName": "vehicleid",
    "globalIdFieldName": "",
    "fields": [
        {
            "name": "vehicleid",
            "type": "esriFieldTypeOID",
            "alias": "vehicleid"
        },
        {
            "name": "name",
            "type": "esriFieldTypeString",
            "alias": "name",
            "length": 64
        },
        {
            "name": "renderer_value",
            "type": "esriFieldTypeString",
            "alias": "renderer_value",
            "length": 32
        },
        {
            "name": "lastseen",
            "type": "esriFieldTypeDate",
            "alias": "lastseen",
            "length": 8
        },
        {
            "name": "speed",
            "type": "esriFieldTypeDouble",
            "alias": "speed"
        },
        {
            "name": "course",
            "type": "esriFieldTypeDouble",
            "alias": "course"
        },
        {
            "name": "is_visible",
            "type": "esriFieldTypeSmallInteger",
            "alias": "is_visible"
        },
        {
            "name": "orgid",
            "type": "esriFieldTypeInteger",
            "alias": "orgid"
        }
    ],
    "geometryType": "esriGeometryPoint",
    "spatialReference": {
        "wkid": 4326,
        "latestWkid": 4326
    },
    "features": [
        {
            "attributes": {
                "vehicleid": 14918,
                "name": "Ungdomslaget Fram - Soløy IL scooter 2",
                "renderer_value": "stopped_scooter",
                "lastseen": 1770471314000,
                "speed": 9.179269,
                "course": 171,
                "is_visible": 0,
                "orgid": 12071
            },
            "geometry": {
                "x": 17.787421058,
                "y": 68.780558562
            }
        },
        {
            "attributes": {
                "vehicleid": 11784,
                "name": "Rælingen kommune - ATV",
                "renderer_value": "stopped_scooter",
                "lastseen": 1748736000000,
                "speed": 0,
                "course": 0,
                "is_visible": 0,
                "orgid": 10072
            },
            "geometry": {
                "x": 12.4411,
                "y": 63.9908
            }
        },
And it is the features part I want to render.

I would prefer a html file only with no backend
```

## M365 Copilot
```
Can you use openstreetmap topo/outdoors or norwegian kartverket as basemap
```

```
merge this into your full polling Deck.gl file and add a legend (speed colors) while we’re at it?
```