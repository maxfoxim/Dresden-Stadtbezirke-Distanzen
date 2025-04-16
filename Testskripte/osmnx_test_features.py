import osmnx as ox
import pandas as pd


place = "Dresden, Germany"

# Grenzen der Längen und Breitengrade
x_links = 13.5
x_rechts = 14.0
y_oben = 51.2
y_unten = 50.90
bbox = [x_links,y_unten,x_rechts,y_oben]
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

gdf = ox.features.features_from_bbox(bbox, tags)
#gdf.to_file( 'OPNV.geojson', driver='GeoJSON' )  

#############

tags = {
        "shop" : "supermarket"
        }

gdf = ox.features.features_from_bbox(bbox, tags)
#gdf.to_file( 'Supermarkt.geojson', driver='GeoJSON' )


####
  
tags = {
        "amenity" : "restaurant"
        }

gdf = ox.features.features_from_bbox(bbox, tags)
#gdf.to_file( 'restaurant.geojson', driver='GeoJSON' )


tags = {
        "amenity" : "kindergarten"
        }

#gdf = ox.features.features_from_bbox(bbox, tags)
#gdf.to_file( 'kindergarten.geojson', driver='GeoJSON' )

