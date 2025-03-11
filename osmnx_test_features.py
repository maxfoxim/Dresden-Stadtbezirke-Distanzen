import osmnx as ox
import pandas as pd


place = "Dresden, Germany"

# Beispiele
tags = {"building": True}
tags = {"amenity": True, "landuse": ["retail", "commercial"], "highway": "bus_stop"}
tags = {"leisure": "park"}

#############

tags = {
        "railway" : "station", 
        "highway" : "railway", 
        "railway" : "tram_stop"
        }

#gdf = ox.features.features_from_place(place, tags)
#gdf.to_file( 'OPNV.geojson', driver='GeoJSON' )  

#############

tags = {
        "shop" : "supermarket"
        }

gdf = ox.features.features_from_place(place, tags)
gdf.to_file( 'Supermarkt.geojson', driver='GeoJSON' )  



