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
Abbuch wenn kleine Isochrone schon drin sind, größere berechnen dann überflüssig
Busverbindungen einbauen https://www.openstreetmap.org/relation/721888#map=14/51.04417/13.74149
"""

dauer_sekunden=[
    5*60,
    10*60,
    15*60,
    20*60,
    25*60,
    30*60,
    35*60,
    40*60
    ]
Fortbewegungsmittel = 'driving-car'  #'foot-walking',  'driving-car' 'cycling-regular'
Use_Gitter = False # Benutze Gitter oder die echten Stadtgrenzen
AUSSER_REICHWEITE = 45*60/60. # angenomme Dauer falls angegebener Isochronendauer außerhalb liegt. Globales Maximum


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
opnv_punkte =         geopandas.read_file("GeoJsons/OPNV.geojson")
supermarkt_punkte =   geopandas.read_file("GeoJsons/supermarkt.geojson")
kindergarten_punkte = geopandas.read_file("GeoJsons/kindergarten.geojson")
restaurants_punkte =  geopandas.read_file("GeoJsons/restaurant.geojson")
schulen_punkte =      geopandas.read_file("GeoJsons/schulen.geojson")

# passendes Format für Darstellung
schule_plot =         geopandas.GeoDataFrame(data=schulen_punkte,        crs='epsg:4326', index = schulen_punkte["name"],      geometry=schulen_punkte["geometry"].to_list()) 
opnv_plot =           geopandas.GeoDataFrame(data=opnv_punkte,           crs='epsg:4326', index = opnv_punkte["name"],         geometry=opnv_punkte["geometry"].to_list()) 
supermarkt_plot =   geopandas.GeoDataFrame(data=supermarkt_punkte,     crs='epsg:4326', index = supermarkt_punkte["name"],   geometry=supermarkt_punkte["geometry"].to_list()) 
kindergarten_plot = geopandas.GeoDataFrame(data=kindergarten_punkte,   crs='epsg:4326', index = kindergarten_punkte["name"], geometry=kindergarten_punkte["geometry"].to_list()) 

schule_plot["name"] = schule_plot.index
opnv_plot["name"] = opnv_plot.index
supermarkt_plot["name"] = supermarkt_plot.index
kindergarten_plot["name"] = kindergarten_plot.index

# Stadtgebiete
#stadtgebiete = geopandas.read_file("GeoJsons/dresdener_gebiete_grenzen.geojson")
stadtgebiete = geopandas.read_file("GeoJsons/dresden_plus_vorstadt.geojson")

stadtgebiete = stadtgebiete[stadtgebiete["name"].notnull()]
stadtgebiete_json = {
    "name":    stadtgebiete["name"].to_list(),
    "geometry":stadtgebiete["geometry"].to_list(),
    "id_str":  stadtgebiete["name"].to_list()

}
print("stadtgebiete_json",stadtgebiete_json)
print("---------")
#Polygone in Geopandas überführen um Schnittmengen berechnen zu können
gitter = erstelle_gitter()
gitter_lebensqualität = erstelle_gitter()
polygon_df = geopandas.GeoDataFrame(data=geo_dict, crs='epsg:4326',index=geo_dict["name"])#, geometry=[polygon_geom])  

if Use_Gitter:     
    isochronen_df =     geopandas.GeoDataFrame(data=gitter,   crs='epsg:4326', index = gitter["name"])  
    lebensqualität_df=  geopandas.GeoDataFrame(data=gitter,   crs='epsg:4326', index = gitter["name"])
else:
    isochronen_df =     geopandas.GeoDataFrame(data=stadtgebiete_json,   crs='epsg:4326', index = stadtgebiete_json["name"]) 
    lebensqualität_df=  geopandas.GeoDataFrame(data=stadtgebiete_json,   crs='epsg:4326', index = stadtgebiete_json["name"])

isochronen_df["Overlap_Distance"] = 0
isochronen_df["Anzahl_OPNV_Punkte"] = 0
isochronen_df["Anzahl_Supermarkt"] = 0
isochronen_df["Anzahl_Kindergarten"] = 0
isochronen_df["Anzahl_Restaurants"] = 0
isochronen_df["Anzahl_Schulen"] = 0
lebensqualität_df["Lebensqualität"] = 1

for Interessenspunkt in Ziel_Adressen:
    isochronen_df[Interessenspunkt] = 0
zwischenspeicher = ""

#print(opnv_punkte)

# Berechne Überlap zwischen Gitter und Distanzen/besonderen Punkten
for index_gebiet, einzelgebiet in isochronen_df.iterrows():
    print("--------------------- ",index_gebiet,"------------------")
    
    ### Einzelpunkte ###
    overlap_schulen = einzelgebiet["geometry"].contains(schulen_punkte["geometry"]) #  Interessenpunkte in Einzelgebiet
    schulen_count = overlap_schulen.sum() # Anzahl der Interessenpunkte in Gebiet
    lebensqualität_df.loc[index_gebiet,"Anzahl_Schulen"] = schulen_count # festschreiben in DF
    print("Anzahl Schulen",schulen_count)
    
    overlap_opnv = einzelgebiet["geometry"].contains(opnv_punkte["geometry"]) #  Interessenpunkte in Einzelgebiet
    stationen_count = overlap_opnv.sum() # Anzahl der Interessenpunkte in Gebiet
    lebensqualität_df.loc[index_gebiet,"Anzahl_OPNV_Punkte"] = stationen_count # festschreiben in DF
    print("Anzahl Haltestellen",stationen_count)
   
    overlap_supermarkt = einzelgebiet["geometry"].contains(supermarkt_punkte["geometry"])
    supermarkt_count = overlap_supermarkt.sum()
    lebensqualität_df.loc[index_gebiet,"Anzahl_Supermarkt"] = supermarkt_count
    print("Anzahl Supermärkte",supermarkt_count) 
    
    overlap_kindergarten = einzelgebiet["geometry"].contains(kindergarten_punkte["geometry"])
    kindergarten_count = overlap_kindergarten.sum()
    lebensqualität_df.loc[index_gebiet,"Anzahl_Kindergarten"] = kindergarten_count
    print("Anzahl Kitas",kindergarten_count)
   
    overlap_restaurants = einzelgebiet["geometry"].contains(supermarkt_punkte["geometry"])
    restaurant_count = overlap_restaurants.sum()
    lebensqualität_df.loc[index_gebiet,"Anzahl_Restaurants"] = restaurant_count
    print("Anzahl Restaurants",restaurant_count) 
    
    #Gesamtqualität
    Lebensqualität = stationen_count + supermarkt_count + kindergarten_count + restaurant_count + schulen_count
    lebensqualität_df.loc[index_gebiet,"Lebensqualität"] = Lebensqualität
    print("Lebensqualität", Lebensqualität)
    
    # Überschneidung zwischen Einzelgebieten und Isochronen berechnen
    for index_isochrone, einzel_isochrone in polygon_df.iterrows():
        #print(index_isochrone,einzel_isochrone["geometry"])
        #print(index_gebiet,gitter)
        if zwischenspeicher != einzel_isochrone["name"]:
            weitere_berechnung = True
            #overlap_area_size_procent_differenz = 0
            overlap_area_size_procent_davor = 0
            overlap_area_size_procent_differenz_summe = 0
            print("Änderung-----")        

        overlap = einzel_isochrone["geometry"].intersects(einzelgebiet["geometry"]) # Gibt es Schnittmenge?
        
        overlap_area = einzel_isochrone["geometry"].intersection(einzelgebiet["geometry"])
        gebiet_size = einzelgebiet["geometry"].area
        overlap_area_size = overlap_area.area
        overlap_area_size_procent = round(overlap_area_size/gebiet_size,4)
        overlap_area_size_procent_differenz = overlap_area_size_procent-overlap_area_size_procent_davor
        overlap_area_size_procent_davor = overlap_area_size_procent
        overlap_area_size_procent_differenz_summe = overlap_area_size_procent_differenz + overlap_area_size_procent_differenz_summe
        #print(einzel_isochrone["geometry"],einzelgebiet["geometry"])
        print(einzel_isochrone["name"], einzel_isochrone["range_value"]/60., overlap, overlap_area_size_procent,overlap_area_size_procent_differenz,overlap_area_size_procent_differenz_summe)



        # falls keine Distanz reicht setze festen Wert
        if (overlap == False)  and  (einzel_isochrone["range_value"]==dauer_sekunden[-1]) :
            isochronen_df.loc[index_gebiet,"Overlap_Distance"] = AUSSER_REICHWEITE*Prio_Wertungen[einzel_isochrone["name"]] + isochronen_df.loc[index_gebiet,"Overlap_Distance"]
            isochronen_df.loc[index_gebiet,einzel_isochrone["name"]] = AUSSER_REICHWEITE
            zwischenspeicher = einzel_isochrone["name"]
            
        if overlap_area_size_procent > 0 and overlap_area_size_procent < 1:
            isochronen_df.loc[index_gebiet,"Overlap_Distance"] =       einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]]*overlap_area_size_procent_differenz + isochronen_df.loc[index_gebiet,"Overlap_Distance"] 
            isochronen_df.loc[index_gebiet,einzel_isochrone["name"]] = round( einzel_isochrone["range_value"]/60.*overlap_area_size_procent_differenz, 2) + isochronen_df.loc[index_gebiet,einzel_isochrone["name"]]
            print("Zwischen 0 und 1:",isochronen_df.loc[index_gebiet,einzel_isochrone["name"]])

            # Falls größtes Gebiet noch nicht 100% abdeckt, restliche Prozent MAXIUM Wert
            if dauer_sekunden[-1] == einzel_isochrone["range_value"] and overlap_area_size_procent < 1:
                isochronen_df.loc[index_gebiet,"Overlap_Distance"] = AUSSER_REICHWEITE*Prio_Wertungen[einzel_isochrone["name"]]*(1-overlap_area_size_procent_differenz_summe) + isochronen_df.loc[index_gebiet,"Overlap_Distance"]
                isochronen_df.loc[index_gebiet,einzel_isochrone["name"]] = round(AUSSER_REICHWEITE*(1-overlap_area_size_procent_differenz_summe),2) + isochronen_df.loc[index_gebiet,einzel_isochrone["name"]]
                print("extra:",isochronen_df.loc[index_gebiet,einzel_isochrone["name"]])


        if overlap_area_size_procent >= 0.999 and weitere_berechnung:
            isochronen_df.loc[index_gebiet,"Overlap_Distance"] =       einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]]*overlap_area_size_procent_differenz + isochronen_df.loc[index_gebiet,"Overlap_Distance"] 
            isochronen_df.loc[index_gebiet,einzel_isochrone["name"]] = round( einzel_isochrone["range_value"]/60.*overlap_area_size_procent_differenz, 2) + isochronen_df.loc[index_gebiet,einzel_isochrone["name"]]
                 
            weitere_berechnung = False
            print("Overlap größer 0.999",isochronen_df.loc[index_gebiet,einzel_isochrone["name"]])

            #print("--",einzel_isochrone["range_value"],einzel_isochrone["name"],einzel_isochrone["range_value"]/60.*Prio_Wertungen[einzel_isochrone["name"]],isochronen_df["Overlap_Distance"].loc[index_gebiet])
        zwischenspeicher = einzel_isochrone["name"]
        
# Farben für Gitter
colormap =                cm.LinearColormap(["green", "yellow", "red"], vmin=isochronen_df.Overlap_Distance.min(), vmax=isochronen_df.Overlap_Distance.max(),)
colormap_lebensqualität = cm.LinearColormap(["red", "yellow", "green"], vmin=0, vmax=lebensqualität_df.Lebensqualität.max(),)

#colormap = linear.YlGn_09.scale(isochronen_df.Overlap_Distance.min(), isochronen_df.Overlap_Distance.max())

gitter_dict = isochronen_df.set_index("id_str")["Overlap_Distance"]
gitter_lebensqualität_dict = lebensqualität_df.set_index("id_str")["Lebensqualität"]


isochronen_df["Gesamtdauer"] = isochronen_df["Overlap_Distance"].apply(str)+ " min"
popup = folium.GeoJsonPopup(
    fields=["name","Gesamtdauer"]+list(Ziel_Adressen.keys()),
    localize=True,
    labels=True,
    )

popup_lebensqualität = folium.GeoJsonPopup(
    fields=["name", "Lebensqualität","Anzahl_OPNV_Punkte","Anzahl_Supermarkt","Anzahl_Kindergarten","Anzahl_Restaurants","Anzahl_Schulen"],
    localize=True,
    labels=True,
    )

popup_stadtbezirke = folium.GeoJsonPopup(
    fields=["name","official_name"],
    localize=True,
    labels=True,
    )

popup_interessante_punkte = folium.GeoJsonPopup(
    fields=["name"],
    localize=True,
    labels=True,
    )

popup_interessante_punkte2 = folium.GeoJsonPopup(
    fields=["name"],
    localize=True,
    labels=True,
    )

popup_interessante_punkte3 = folium.GeoJsonPopup(
    fields=["name"],
    localize=True,
    labels=True,
    )

popup_interessante_punkte4 = folium.GeoJsonPopup(
    fields=["name"],
    localize=True,
    labels=True,
    )

print("DOPPELTE")
print(isochronen_df[isochronen_df.duplicated(keep=False)])


folium.GeoJson(schule_plot,
               name="Schulen",
               popup=popup_interessante_punkte,
               style_function=lambda feature: {
                    "fillColor": "blue",
                    "color": "blue",
                    "weight": 1,
                    "fillOpacity": 0.9
                }
               ).add_to(m)

folium.GeoJson(opnv_plot,
               name="OPNV",
               marker=folium.Circle(radius=40, fill_color="green", fill_opacity=0.6, color="black", weight=1),
               popup=popup_interessante_punkte2,
               style_function=lambda feature: {
                    "fillColor": "green",
                    "color": "green",
                    "weight": 1,
                    "fillOpacity": 0.9,
                    "markerColor":"green"
                }
               ).add_to(m)

folium.GeoJson(kindergarten_plot,
               name="Kindergarten",
               marker=folium.Circle(radius=40, fill_color="orange", fill_opacity=0.9, color="black", weight=1),
               popup=popup_interessante_punkte3,
               style_function=lambda feature: {
                    "fillColor": "orange",
                    "color": "orange",
                    "weight": 1,
                    "fillOpacity": 0.9,
                    "markerColor":"orange"
                }
               ).add_to(m)

folium.GeoJson(supermarkt_plot,
               name="Supermarkt",
               popup=popup_interessante_punkte4,
               marker=folium.Circle(radius=40, fill_color="red", fill_opacity=0.4, color="black", weight=1),
               style_function=lambda feature: {
                    "fillColor": "red",
                    "color": "red",
                    "weight": 1,
                    "fillOpacity": 0.9,
                    "markerColor":"red"
                }
               ).add_to(m)

folium.GeoJson(isochronen_df,
               show=False,
               name="Gitter Entfernungen",
               popup=popup,
               style_function=lambda feature: {
                    "fillColor": colormap(gitter_dict[feature["id"]]),
                    "color": "black",
                    "weight": 1,
                    "dashArray": "5, 5",
                    "fillOpacity": 0.9
                }).add_to(m)


folium.GeoJson(lebensqualität_df,
               show=False,
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



"""
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
"""
#print("DF: ",polygon_df)
#print("Gitter: ",isochronen_df)
#isochronen_df.to_csv("gitter.csv")

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

print(isochronen_df)

print(lebensqualität_df)

# Speichern
file_name = 'Dresden-'
m.save(file_name + Fortbewegungsmittel +'.html')