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
Dauer pro Gitterkachel
Abbuch wenn kleine Isochrone schon drin sind, größere berechnen dann überflüssig
Gebiete statt Kacheln -> 
    Überschneidung Mittelwert Zeiten (Prozent Überlapp)
"""

dauer_sekunden=[5*60,10*60,20*60,30*60]
Fortbewegungsmittel = 'driving-car'  #'foot-walking',  'driving-car' 'cycling-regular'
Use_Gitter = False # Benutze Gitter oder die echten Stadtgrenzen
AUSSER_REICHWEITE = 4200/60. # angenomme Dauer falls angegebener Isochronendauer außerhalb liegt. Globales Maximum


# Gewünschte Zieladressen
Ziel_Adressen={
    "Robotron":[51.010042433360255, 13.701267488585485],
    "Schule":[50.99507147504863, 13.80808908738222],
    "Kletterarena":[51.040951530745545, 13.715802737639914],
     "Großeltern":[51.05654509189485, 13.895285953791621],
     "Dresden Zentrum":[51.05054037636587, 13.736688817986499],
     "Johanna": [51.04399714777088, 13.812859847360748],
     "Kita":[51.058520,13.788871]
}

Prio_Wertungen={
    "Robotron":2,
    "Schule":5,
    "Kletterarena":1,
    "Großeltern":1,
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
    return { 
            "name":range(len(rechtecke)), 
            "geometry":rechtecke, 
            "id_str":range_len
            }

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

# Berechne für alle angegebenen Ziele die Isochronen
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

    # Für jede Distanz der Isochronen
    for isochrone in iso['features'][::]: # Sortiere von klein nach groß
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
        
        
    for isochrone in iso['features'][::-1]: # sortiere von groß nach klein (besser für Überlappung)
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


# Interessante Punkte
opnv_punkte = geopandas.read_file("GeoJsons/OPNV.geojson")
supermarkt_punkte = geopandas.read_file("GeoJsons/supermarkt.geojson")
kindergarten_punkte = geopandas.read_file("GeoJsons/kindergarten.geojson")
restaurants_punkte = geopandas.read_file("GeoJsons/restaurant.geojson")

# Stadtgebiete
stadtgebiete = geopandas.read_file("GeoJsons/dresdener_gebiete_grenzen.geojson")
stadtgebiete = stadtgebiete[stadtgebiete["name"].notnull()]
stadtgebiete_json = {
    "name":stadtgebiete["name"].to_list(),
    #"name":stadtgebiete.index.to_list(),
    "geometry":stadtgebiete["geometry"].to_list(),
    #"id_str": [str(i) for i in range(len(stadtgebiete))],
    "id_str": stadtgebiete["name"].to_list()

}
print("stadtgebiete_json",stadtgebiete_json)
print("---------")
#Polygone in Geopandas überführen um Schnittmengen berechnen zu können
gitter = erstelle_gitter()
gitter_lebensqualität = erstelle_gitter()
polygon_df = geopandas.GeoDataFrame(data=geo_dict, crs='epsg:4326',index=geo_dict["name"])#, geometry=[polygon_geom])  

if Use_Gitter:     
    gitter_df =                geopandas.GeoDataFrame(data=gitter,   crs='epsg:4326',index=  gitter["name"])#, geometry=[polygon_geom])  
    gitter_lebensqualität_df=  geopandas.GeoDataFrame(data=gitter,   crs='epsg:4326',index = gitter["name"])#, geometry=[polygon_geom])  
else:
    gitter_df =                geopandas.GeoDataFrame(data=stadtgebiete_json,   crs='epsg:4326',index=  stadtgebiete_json["name"])#, geometry=[polygon_geom])  
    gitter_lebensqualität_df=  geopandas.GeoDataFrame(data=stadtgebiete_json,   crs='epsg:4326',index = stadtgebiete_json["name"])#, geometry=[polygon_geom])  

gitter_df["Overlap_Distance"] = 0
gitter_df["Anzahl_OPNV_Punkte"] = 0
gitter_df["Anzahl_Supermarkt"] = 0
gitter_df["Anzahl_Kindergarten"] = 0
gitter_df["Anzahl_Restaurants"] = 0
gitter_lebensqualität_df["Lebensqualität"] = 1

for Interessenspunkt in Ziel_Adressen:
    gitter_df[Interessenspunkt] = 0
zwischenspeicher = ""

#print(opnv_punkte)

# Berechne Überlap zwischen Gitter und Distanzen/besonderen Punkten
for index_gebiet, einzelgebiet in gitter_df.iterrows():
    print("--------------------- ",index_gebiet,"------------------")
    
    ### Einzelpunkte ###
    overlap_opnv = einzelgebiet["geometry"].contains(opnv_punkte["geometry"]) #  Interessenpunkte in Einzelgebiet
    stationen_count = overlap_opnv.sum() # Anzahl der Interessenpunkte in Gebiet
    gitter_lebensqualität_df.loc[index_gebiet,"Anzahl_OPNV_Punkte"] = stationen_count # festschreiben in DF
    print("Anzahl Haltestellen",stationen_count)
   
    overlap_supermarkt = einzelgebiet["geometry"].contains(supermarkt_punkte["geometry"])
    supermarkt_count = overlap_supermarkt.sum()
    gitter_lebensqualität_df.loc[index_gebiet,"Anzahl_Supermarkt"] = supermarkt_count
    print("Anzahl Supermärkte",supermarkt_count) 
    
    overlap_kindergarten = einzelgebiet["geometry"].contains(kindergarten_punkte["geometry"])
    kindergarten_count = overlap_kindergarten.sum()
    gitter_lebensqualität_df.loc[index_gebiet,"Anzahl_Kindergarten"] = kindergarten_count
    print("Anzahl Kitas",kindergarten_count)
   
    overlap_restaurants = einzelgebiet["geometry"].contains(supermarkt_punkte["geometry"])
    restaurant_count = overlap_restaurants.sum()
    gitter_lebensqualität_df.loc[index_gebiet,"Anzahl_Restaurants"] = restaurant_count
    print("Anzahl Restaurants",restaurant_count) 
    
    #Gesamtqualität
    Lebensqualität = stationen_count + supermarkt_count + kindergarten_count + restaurant_count 
    gitter_lebensqualität_df.loc[index_gebiet,"Lebensqualität"] = Lebensqualität
    print("Lebensqualität", Lebensqualität)
    
    # Überschneidung zwischen Einzelgebieten und Isochronen berechnen
    for index_u, einzel_isochrone in polygon_df.iterrows():
        #print(index_u,einzel_isochrone["geometry"])
        #print(index_gebiet,gitter)
        if zwischenspeicher != einzel_isochrone["name"]:
            weitere_berechnung = True
            #overlap_area_size_procent_differenz = 0
            overlap_area_size_procent_davor = 0
            print("Änderung",zwischenspeicher,einzel_isochrone["name"])        

        overlap = einzel_isochrone["geometry"].intersects(einzelgebiet["geometry"]) # Gibt es Schnittmenge?
        
        overlap_area = einzel_isochrone["geometry"].intersection(einzelgebiet["geometry"])
        gebiet_size = einzelgebiet["geometry"].area
        overlap_area_size = overlap_area.area
        overlap_area_size_procent = round(overlap_area_size/gebiet_size,4)
        overlap_area_size_procent_differenz = overlap_area_size_procent-overlap_area_size_procent_davor
        overlap_area_size_procent_davor = overlap_area_size_procent
        #print(einzel_isochrone["geometry"],einzelgebiet["geometry"])
        print(einzel_isochrone["name"], einzel_isochrone["range_value"], overlap, overlap_area_size_procent,overlap_area_size_procent_differenz)



        # falls keine Distanz reicht setze festen Wert
        if (overlap == False)  and  (einzel_isochrone["range_value"]==dauer_sekunden[-1]) :
            gitter_df.loc[index_gebiet,"Overlap_Distance"] = AUSSER_REICHWEITE*Prio_Wertungen[einzel_isochrone["name"]] + gitter_df.loc[index_gebiet,"Overlap_Distance"]
            gitter_df.loc[index_gebiet,einzel_isochrone["name"]] = AUSSER_REICHWEITE
            zwischenspeicher = einzel_isochrone["name"]
            
        if overlap_area_size_procent >0 and overlap_area_size_procent < 1:
            gitter_df.loc[index_gebiet,"Overlap_Distance"] = einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]]*overlap_area_size_procent_differenz + gitter_df.loc[index_gebiet,"Overlap_Distance"] 
            gitter_df.loc[index_gebiet,einzel_isochrone["name"]] = einzel_isochrone["range_value"]/60.*overlap_area_size_procent_differenz
            print("0-1",gitter_df.loc[index_gebiet,einzel_isochrone["name"]])

        if overlap_area_size_procent >= 1.0 and weitere_berechnung:
            gitter_df.loc[index_gebiet,"Overlap_Distance"] = einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]]*overlap_area_size_procent_differenz + gitter_df.loc[index_gebiet,"Overlap_Distance"] 
            gitter_df.loc[index_gebiet,einzel_isochrone["name"]] = einzel_isochrone["range_value"]/60.*overlap_area_size_procent_differenz
            weitere_berechnung = False
            print("1",gitter_df.loc[index_gebiet,einzel_isochrone["name"]])

            #print("--",einzel_isochrone["range_value"],einzel_isochrone["name"],einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]],gitter_df["Overlap_Distance"].loc[index_gebiet])
        zwischenspeicher = einzel_isochrone["name"]
        
# Farben für Gitter
colormap = cm.LinearColormap(["green", "yellow", "red"], vmin=gitter_df.Overlap_Distance.min(), vmax=gitter_df.Overlap_Distance.max(),)
colormap_lebensqualität = cm.LinearColormap(["red", "yellow", "green"], vmin=0, vmax=gitter_lebensqualität_df.Lebensqualität.max(),)

#colormap = linear.YlGn_09.scale(gitter_df.Overlap_Distance.min(), gitter_df.Overlap_Distance.max())

gitter_dict = gitter_df.set_index("id_str")["Overlap_Distance"]
gitter_lebensqualität_dict = gitter_lebensqualität_df.set_index("id_str")["Lebensqualität"]


gitter_df["Gesamtdauer"] = gitter_df["Overlap_Distance"].apply(str)+ " min"
popup = folium.GeoJsonPopup(
    fields=["name","Gesamtdauer"]+list(Ziel_Adressen.keys()),
    localize=True,
    labels=True,
    )

popup_lebensqualität = folium.GeoJsonPopup(
    fields=["name", "Lebensqualität","Anzahl_OPNV_Punkte","Anzahl_Supermarkt","Anzahl_Kindergarten","Anzahl_Restaurants"],
    localize=True,
    labels=True,
    )

popup_stadtbezirke = folium.GeoJsonPopup(
    fields=["name","official_name"],
    localize=True,
    labels=True,
    )

folium.GeoJson(gitter_df,
               name="Gitter",
               popup=popup,
               style_function=lambda feature: {
                    "fillColor": colormap(gitter_dict[feature["id"]]),
                    "color": "black",
                    "weight": 1,
                    "dashArray": "5, 5",
                    "fillOpacity": 0.5
                }).add_to(m)


folium.GeoJson(gitter_lebensqualität_df,
               name="Gitter Lebensqualität",
               popup=popup_lebensqualität,
               style_function=lambda feature: {
                    "fillColor": colormap_lebensqualität(gitter_lebensqualität_dict[feature["id"]]),
                    "color": "black",
                    "weight": 1,
                    "dashArray": "5, 5",
                    "fillOpacity": 0.5
                }).add_to(m)


colormap.caption = "Dauer"
colormap.add_to(m)
colormap_lebensqualität.caption = "Anzahl Punkte"
colormap_lebensqualität.add_to(m)


folium.GeoJson(stadtgebiete,
               name="Stadtgebiete",
               popup=popup_stadtbezirke,
               style_function=lambda feature: {
                    "fillColor": "blue",
                    "color": "black",
                    "weight": 2,
                    "dashArray": "5, 5",
                    "fillOpacity": 0.3
                }).add_to(m)

#print("DF: ",polygon_df)
#print("Gitter: ",gitter_df)
#gitter_df.to_csv("gitter.csv")

# Berechne Überschneidungen aller Isochronen
ausgabe = polygon_df["geometry"].loc[(polygon_df["name"] == "Robotron") & (polygon_df["range_value"] == dauer_sekunden[-1])]
for count in polygon_df["count"].loc[polygon_df["range_value"] == dauer_sekunden[-1]]:
    ausgabe = ausgabe.intersection(
        polygon_df["geometry"].loc[(polygon_df["count"] == count)], align=False)
    print(ausgabe)

#Overlap der weitesten Isochronen
#style_function = lambda x: {'fillColor': 'red',                          'color':'red'}
#folium.GeoJson(ausgabe,style_function=style_function,name="Overlap",show=False).add_to(m)
folium.LayerControl(show=False).add_to(m)

print(gitter_df)

print(gitter_lebensqualität_df)

# Speichern
file_name = 'Dresden-'
m.save(file_name + Fortbewegungsmittel +'.html')