import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import openrouteservice as ors  # Für die Berechnung der Distanzen
import secret_api   # eigene Datei mit API. Dateiinhalt:   api="5b3c....."
import time
import folium

# Gewünschte Zieladressen
Ziel_Adressen={
    #"Zu_Hause":[51.05885076550623, 13.766713420144118],
    "Robotron":[51.010042433360255, 13.701267488585485],
    "Schule":[50.99507147504863, 13.80808908738222],
    "Kletterarena":[51.040951530745545, 13.715802737639914],
    "Großeltern":[51.05654509189485, 13.895285953791621],
    #"Dresden Zentrum":[51.05054037636587, 13.736688817986499],
    "Johanna": [51.04399714777088, 13.812859847360748]
}

client = ors.Client(key=secret_api.api)

m = folium.Map(location=[51.05885076550623, 13.766713420144118], tiles='OpenStreetMap', zoom_start=13)


# Some coordinate in Berlin
coordinate = [[13.384116, 52.533558]]
coordinate = list(Ziel_Adressen.values())

print(coordinate)
farben = ["00ff00","lightgreen","red","orange","pink","darkgreen"]
# Also create a Popup with Population count within isochrones
i=0
for coordi in Ziel_Adressen:
    print(i,coordi,farben[i])
    iso = client.isochrones(
    locations=[Ziel_Adressen[coordi][::-1]],
    profile='driving-car',  #'foot-walking',  'driving-car' 'cycling-regular'
    range=[600,900,1200,1500,1800],  # Seconds
    validate=False,
    #attributes=['total_pop']
    )
    #print("iso",iso)

    fg = folium.FeatureGroup(name=coordi, control=True, overlay=True).add_to(m)

    for isochrone in iso['features'][::-1]:
        #print(isochrone)
        
        folium.Polygon(locations=[list(reversed(coord)) for coord in isochrone['geometry']['coordinates'][0]],
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

folium.LayerControl().add_to(m)


file_name = 'my_folium_map'
m.save(file_name + '.html')