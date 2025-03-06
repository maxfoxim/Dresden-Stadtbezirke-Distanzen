import pandas as pd
from bs4 import BeautifulSoup as bs
import openrouteservice as ors  # Für die Berechnung der Distanzen
import secret_api   # eigene Datei mit API. Dateiinhalt:   api="5b3c....."
import folium
from shapely.geometry import Polygon, LineString, Point
import geopandas
import numpy as np
from branca.colormap import linear
import branca.colormap as cm
""" 
Ideen:
Aufteilung nach Fahrrad, Auto
Anzahl relevanter Punkte: Einkaufsmarkt, Haltestellen, 
"""

dauer_sekunden=[5*60,10*60,20*60,30*60]
Fortbewegungsmittel = 'driving-car'  #'foot-walking',  'driving-car' 'cycling-regular'

# Gewünschte Zieladressen
Ziel_Adressen={
    "Robotron":[51.010042433360255, 13.701267488585485],
    "Schule":[50.99507147504863, 13.80808908738222],
    "Kletterarena":[51.040951530745545, 13.715802737639914],
    "Großeltern":[51.05654509189485, 13.895285953791621],
    #"Dresden Zentrum":[51.05054037636587, 13.736688817986499],
    "Johanna": [51.04399714777088, 13.812859847360748],
    "Kita":[51.058520,13.788871]
}

Prio_Wertungen={
    "Robotron":2,
    "Schule":5,
    "Kletterarena":1,
    "Großeltern":2,
    "Dresden Zentrum":1,
    "Johanna": 1,
    "Kita":5
}

def erstelle_gitter(Anzahl_Punkte=30):
    """ 
    Gleichmäßiges Gitter über die Karte erstellen
    """
    
    # Grenzen der Längen und Breitengrade
    x_links = 13.5
    x_rechts = 14.0
    y_oben = 51.2
    y_unten = 50.90
        
    x = np.linspace(x_links, x_rechts, Anzahl_Punkte)
    y = np.linspace(y_unten, y_oben, Anzahl_Punkte)
    
    # Erstelle Ecken
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
    
    range_len = [str(i) for i in range(len(rechtecke))]
    return { "name":range(len(rechtecke)), "geometry":rechtecke, "id_str":range_len}

# Erstelle Verbindung zu ORS (Berechnung der Isochrone)
client = ors.Client(key=secret_api.api)

# Erstelle grundlegende Karte
m = folium.Map(location=[51.05885076550623, 13.766713420144118], tiles='OpenStreetMap', zoom_start=12)

# Farben für Isochrone (optional)
# farben = ["00ff00","lightgreen","red","orange","pink","darkgreen"]
geo_dict={"name":[],"geometry":[],"range_value":[],"count":[]}
geo_arrays = []
i=0
counter=0


for coordi in Ziel_Adressen:
    print(i,coordi)
    
    # Berechnung der Isochrone
    iso = client.isochrones(
    locations=[Ziel_Adressen[coordi][::-1]], # Koordinaten umdrehen
    profile=Fortbewegungsmittel,
    range=dauer_sekunden,  # Seconds
    validate=False
    )

    # Gruppe der Isochrone
    fg = folium.FeatureGroup(name=coordi, control=True, overlay=True, show=False).add_to(m)

    for isochrone in iso['features'][::]:
        #print(isochrone)
        locations=[list(reversed(coord)) for coord in isochrone['geometry']['coordinates'][0]]
        #print("locations",locations)
        geo_dict["name"].append(coordi)
        geo_dict["range_value"].append(int(isochrone["properties"]["value"]))
        geo_dict["count"].append(counter)
        counter = counter + 1
        lat = [i[1] for i in locations]
        long = [i[0] for i in locations]
        polygon_geom = Polygon(zip(lat, long))
        geo_dict["geometry"].append(polygon_geom)
        print("Isochrone Zeit:", isochrone["properties"]["value"]/60)
        
        
    for isochrone in iso['features'][::-1]:
        locations=[list(reversed(coord)) for coord in isochrone['geometry']['coordinates'][0]]

        # Isochrones Polygon
        folium.Polygon(locations=locations,
                    show=True,
                    fill_color="blue",
                    fill_opacity=0.15,
                    popup=folium.Popup(coordi+" "+str(round(isochrone["properties"]["value"]/60)) + " min"),
                    ).add_to(fg)
        
        # Mittelpunkt und Marker der Polygone
        folium.map.Marker((Ziel_Adressen[coordi]),  # reverse coords due to weird folium lat/lon syntax
                          icon=folium.Icon(color='lightgray',
                                           icon_color='#cc0000',
                                           icon='home',
                                           prefix='fa',
                                           ), popup=coordi,).add_to(m)
                
    i=i+1




#Polygone in Geopandas überführen um Schnittmengen berechnen zu können
gitter=erstelle_gitter()
polygon_df = geopandas.GeoDataFrame(data=geo_dict, crs='epsg:4326',index=geo_dict["name"])#, geometry=[polygon_geom])       
gitter_df =  geopandas.GeoDataFrame(data=gitter,   crs='epsg:4326',index=  gitter["name"])#, geometry=[polygon_geom])       
gitter_df["Overlap_Distance"] = 0
zwischenspeicher = ""
AUSSER_REICHWEITE = 4200/60.

# Berechne Überlap zwischen Gitter und Distanzen
for index_g, gitter in gitter_df.iterrows():
    print("--------------------- ",index_g,"------------------")
    for index_u, umkreis in polygon_df.iterrows():
        #print(index_u,umkreis["geometry"])
        #print(index_g,gitter)
        overlap = umkreis["geometry"].intersects(gitter["geometry"])
        print(umkreis["range_value"],umkreis["name"],overlap)
        #print(umkreis["geometry"],gitter["geometry"])
        
        # falls keine Distanz reicht setze festen Wert
        if (umkreis["range_value"]==dauer_sekunden[-1]) and (overlap == False):
            gitter_df.loc[index_g,"Overlap_Distance"] = AUSSER_REICHWEITE*Prio_Wertungen[umkreis["name"]] + gitter_df["Overlap_Distance"].loc[index_g]
            #print("--Außer Bereich--",umkreis["range_value"],umkreis["name"],AUSSER_REICHWEITE*Prio_Wertungen[umkreis["name"]],gitter_df["Overlap_Distance"].loc[index_g])
            zwischenspeicher = umkreis["name"]
            
        if overlap and umkreis["name"] != zwischenspeicher:
            #gitter_df["Overlap_Distance"].loc[index_g] = umkreis["range_value"]/60.*Prio_Wertungen[umkreis["name"]] + gitter_df["Overlap_Distance"].loc[index_g]
            gitter_df.loc[index_g,"Overlap_Distance"] = umkreis["range_value"]/60.*Prio_Wertungen[umkreis["name"]] + gitter_df["Overlap_Distance"].loc[index_g]

            #print("--",umkreis["range_value"],umkreis["name"],umkreis["range_value"]/60.*Prio_Wertungen[umkreis["name"]],gitter_df["Overlap_Distance"].loc[index_g])
            zwischenspeicher = umkreis["name"]
        
# Farben für Gitter
colormap = cm.LinearColormap(["green", "yellow", "red"], vmin=gitter_df.Overlap_Distance.min(), vmax=gitter_df.Overlap_Distance.max(),)
#colormap = linear.YlGn_09.scale(gitter_df.Overlap_Distance.min(), gitter_df.Overlap_Distance.max())


gitter_dict = gitter_df.set_index("id_str")["Overlap_Distance"]
gitter_df["Labels"] = gitter_df["name"].apply(str) +": " + gitter_df["Overlap_Distance"].apply(str)+ " min"
popup = folium.GeoJsonPopup(fields=["Labels"])

folium.GeoJson(gitter_df,
               name="Gitter",
               popup=popup,
               style_function=lambda feature: {
                    "fillColor": colormap(gitter_dict[feature["id"]]),
                    "color": "black",
                    "weight": 1,
                    "dashArray": "5, 5",
                    "fillOpacity": 0.5
                }
               ).add_to(m)

colormap.caption = "Dauer"
colormap.add_to(m)

#print("DF: ",polygon_df)
#print("Gitter: ",gitter_df)
#gitter_df.to_csv("gitter.csv")

# Berechne Überschneidungen aller Isochronen
ausgabe=polygon_df["geometry"].loc[ (polygon_df["name"] == "Robotron") & (polygon_df["range_value"] == dauer_sekunden[-1])]
for count in polygon_df["count"].loc[polygon_df["range_value"] == dauer_sekunden[-1]]:
    ausgabe=ausgabe.intersection(polygon_df["geometry"].loc[(polygon_df["count"] == count)],align=False)
    print(ausgabe)

style_function = lambda x: {'fillColor': 'red',
                            'color':'red'}
folium.GeoJson(ausgabe,style_function=style_function,name="Overlap").add_to(m)
folium.LayerControl().add_to(m)

# Speichern
file_name = 'Dresden-'
m.save(file_name + Fortbewegungsmittel +'.html')