import pandas as pd
from bs4 import BeautifulSoup as bs
import openrouteservice as ors  # Für die Berechnung der Distanzen
import secret_api   # eigene Datei mit API. Dateiinhalt:   api="5b3c....."
import folium
from shapely.geometry import Polygon, LineString, Point
import geopandas
import numpy as np
""" 
Ideen:
Aufteilung nach Fahrrad, Auto
Überlapp aller Ziele mit Gewichtung
Farbskala der Gesamtzeiten
"""



# Gewünschte Zieladressen
Ziel_Adressen={
    #"Zu_Hause":[51.05885076550623, 13.766713420144118],
    "Robotron":[51.010042433360255, 13.701267488585485],
    #"Schule":[50.99507147504863, 13.80808908738222],
    #"Kletterarena":[51.040951530745545, 13.715802737639914],
    #"Großeltern":[51.05654509189485, 13.895285953791621],
    #"Dresden Zentrum":[51.05054037636587, 13.736688817986499],
    #"Johanna": [51.04399714777088, 13.812859847360748]
}

def erstelle_gitter(Anzahl_Punkte=10):
    x_links = 13.5
    x_rechts = 13.97
    y_oben = 51.2
    y_unten = 50.91
        
    x = np.linspace(x_links, x_rechts, Anzahl_Punkte)
    y = np.linspace(y_unten, y_oben, Anzahl_Punkte)
    
    rechtecke = []
    i = 0
    j = 0
    while i < len(x)-1:
        while j < len(y)-1:
            #print(i,j)
            rechtecke.append(Polygon([
                            (x[i],y[j]),
                            (x[i+1],y[j]),
                            (x[i+1],y[j+1]),
                            (x[i],y[j+1])]))
            j=j+1
        j=0
        i=i+1
    
    return {"name":range(len(rechtecke)),"geometry":rechtecke}

gitter=erstelle_gitter()

client = ors.Client(key=secret_api.api)

m = folium.Map(location=[51.05885076550623, 13.766713420144118], tiles='OpenStreetMap', zoom_start=13)

farben = ["00ff00","lightgreen","red","orange","pink","darkgreen"]
geo_dict={"name":[],"geometry":[],"range_value":[],"count":[]}
geo_arrays = []
i=0
counter=0
for coordi in Ziel_Adressen:
    print(i,coordi,farben[i])
    iso = client.isochrones(
    locations=[Ziel_Adressen[coordi][::-1]],
    profile='driving-car',  #'foot-walking',  'driving-car' 'cycling-regular'
    range=[1800,900],#,900,1200,1500,1800],  # Seconds
    validate=False
    )

    fg = folium.FeatureGroup(name=coordi, control=True, overlay=True).add_to(m)

    for isochrone in iso['features'][::-1]:
        #print(isochrone)
        locations=[list(reversed(coord)) for coord in isochrone['geometry']['coordinates'][0]]
        #print("locations",locations)
        geo_dict["name"].append(coordi)
        geo_dict["range_value"].append(int(isochrone["properties"]["value"]))
        geo_dict["count"].append(counter)
        counter = counter +1
        lat=[ i[1] for i in locations]
        long=[ i[0] for i in locations]
        polygon_geom = Polygon(zip(lat,long))
        geo_dict["geometry"].append(polygon_geom)

        
        folium.Polygon(locations=locations,
                    fillColor="00ff00",#farben[i],
                    #color="black",
                    popup=folium.Popup(coordi+" "+str(round(isochrone["properties"]["value"]/60)) + " min"),
                    opacity=0.5).add_to(fg)
        
        folium.map.Marker((Ziel_Adressen[coordi]),  # reverse coords due to weird folium lat/lon syntax
                    icon=folium.Icon(color='lightgray',
                                       icon_color='#cc0000',
                                       icon='home',
                                       prefix='fa',
                                       ), popup=coordi,).add_to(fg)
        
        
    i=i+1


#Polygone in Geopandas überführen
polygon_df = geopandas.GeoDataFrame(data=geo_dict, crs='epsg:4326',index=geo_dict["name"])#, geometry=[polygon_geom])       
gitter_df = geopandas.GeoDataFrame( data=gitter,   crs='epsg:4326',index=gitter["name"])#, geometry=[polygon_geom])       

for index_g,gitter in gitter_df.iterrows():
    for index_u,umkreis in polygon_df.iterrows():
        #print(index_u,umkreis["geometry"])
        #print(index_g,gitter)
        overlap=umkreis["geometry"].overlaps(gitter["geometry"])
        print(overlap)

folium.GeoJson(gitter_df,fillColor="yellow",color="yellow",name="Gitter").add_to(m)

print("DF: ",polygon_df)
print("Gitter: ",gitter_df)

# Berechne Überschneindungen
#ausgabe=polygon_df["geometry"].loc[ (polygon_df["name"] == "Robotron") & (polygon_df["range_value"] == 900)]
ausgabe=polygon_df["geometry"].loc[ (polygon_df["count"] == 0)]


print("Ausgabe",ausgabe)
for count in polygon_df["count"]:
    ausgabe=ausgabe.intersection(polygon_df["geometry"].loc[(polygon_df["count"] == count)],align=False)

folium.GeoJson(ausgabe,fillColor="red",color="red",name="Overlap").add_to(m)
 
#print("Ausgabe",ausgabe)

folium.LayerControl().add_to(m)
file_name = 'my_folium_map'
m.save(file_name + '.html')