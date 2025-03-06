import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import openrouteservice  # Für die Berechnung der Distanzen
import secret_api   # eigene Datei mit API. Dateiinhalt:   api="5b3c....."
import time
import codecs
import json
import openpyxl

""" 
TO DO:
- Geojson am Ende mit Excelinhalt genieren (mouse over?)
"""

Benutze_wikipedia = False
Fortbewegung='driving-car'  #'foot-walking',  'driving-car' 'cycling-regular'

# Gewünschte Zieladressen
Ziel_Adressen={
    #"Zu_Hause":[51.05885076550623, 13.766713420144118],
    "Robotron":[51.010042433360255, 13.701267488585485],
    "Schule":[50.99507147504863, 13.80808908738222],
    "Kletterarena":[51.040951530745545, 13.715802737639914],
    "Großeltern":[51.05654509189485, 13.895285953791621],
    "Dresden Zentrum":[51.05054037636587, 13.736688817986499],
    "Kita":[51.058520,13.788871]

}

######### ######### ######### #########

def distanzen_berechnen(Start,Ende,datei):
    coords=(Start,Ende)
    client = openrouteservice.Client(key=secret_api.api) # Specify your personal API key
    ausgabe = client.directions(coords,profile=Fortbewegung,geometry= 'true',format_out="geojson")
    #print(ausgabe)
    distanz=ausgabe["features"][0]["properties"]["summary"]["distance"]
    dauer=ausgabe["features"][0]["properties"]["summary"]["duration"]/60.
    bbox=ausgabe["features"][0]["bbox"]
    print("Distanz",distanz/1000,"Dauer",dauer)
    return round(int(distanz)/1000,2), int(dauer) 




Namen_arr,URL_arr=[],[]
Long_arr,Lat_arr=[],[]
gemeinde = []

if Benutze_wikipedia:
    tables=pd.read_csv("wikipedia_download_liste.csv")
    df=tables
    for index,row in enumerate(df["Name"]):
        print(index,"ROHE REIHE",row)

        row=row.replace("'","")
        Werte=row.split(", ")
        
        Name=Werte[0]
        Name=Name.replace("(","")
        Name=Name.replace(")","")    

        URL = "https://de.wikipedia.org"+Werte[1]
        URL = URL.replace("))",")")  

        URL_extract=Werte[1]
        if URL_extract.find("(")>-1:
            URL_extract=URL_extract.replace("))",")")  
        else:
            URL_extract=URL_extract.replace(")","")  

        # Sonderzeichen ersetzen
        URL_extract=URL_extract.replace("/wiki/","")
        URL_extract=URL_extract.replace("%C3%A4","ä")   
        URL_extract=URL_extract.replace("%C3%BC","ü")
        URL_extract=URL_extract.replace("%C3%B6","ö")
        URL_extract=URL_extract.replace("%C3%9F","ß")

        URL_API = "https://de.wikipedia.org/w/api.php"  # deutsche API Endstelle

        PARAMS = {
            "action": "query",
            "format": "json",
            "titles": URL_extract, # Der Name des Wikipedia Artikels
            "prop": "coordinates"
        }
        S = requests.Session()

        # Abfrage der Koordinaten in Wikipedia
        print(Name,URL,"URL_Extract: ",URL_extract)
        R = S.get(url=URL_API, params=PARAMS)
        DATA = R.json()
        PAGES = DATA['query']['pages']
        for k, v in PAGES.items():
            try:
                latitude=float(v['coordinates'][0]['lat'])
                longitude=float(v['coordinates'][0]['lon'])
                Namen_arr.append(Name)
                Long_arr.append(longitude)
                Lat_arr.append(latitude)
                URL_arr.append(URL)
                print(latitude,longitude)

            except:
                print("Problem, keine Koordinaten gefunden.")
        print("----------------------")
        PD_Adressen=pd.DataFrame(data={"Name":Namen_arr,"Lat":Lat_arr,"Long":Long_arr,"URL":URL_arr})

else: #Berechne mit OVerpass Daten
    with codecs.open("stadtteil_zentrum.geojson", 'r', encoding='utf-8') as f:
        stadtteile_overpass=json.load(f)
    
    for stadtteil in stadtteile_overpass["features"]:
        Namen_arr.append(stadtteil["properties"]["name"])
        Lat_arr.append(stadtteil["geometry"]["coordinates"][1])
        Long_arr.append(stadtteil["geometry"]["coordinates"][0])
        try:
            gemeinde.append(stadtteil["properties"]["is_in"])
        except:
            gemeinde.append("-")
    PD_Adressen=pd.DataFrame(data={"Name":Namen_arr,"Lat":Lat_arr,"Long":Long_arr,"Gemeinde":gemeinde})

### Distanzen bestimmen
print("\n\n\n-----------------------------")

# Initaliserung
for Ziele in Ziel_Adressen:
     PD_Adressen[Ziele+"_Distanz"]=0
     PD_Adressen[Ziele+"_Dauer"]=0

counter=1
for index,row in PD_Adressen.iterrows(): # die Gebiete durchgehen
    for Ziele in Ziel_Adressen: # die Ziele durchgehen
        print(counter,")    ",index,"Von",Ziele," nach ",row["Name"])
        Ende=list(reversed(Ziel_Adressen[Ziele]))
        Start=[row["Long"],row["Lat"]]
        print("GPS: Von",Start," nach ",Ende)

        # Berechnung der Distanz und Dauer
        try:
            distanz, dauer=distanzen_berechnen(Start,Ende,None)
        except:
            distanz, dauer = -1, -1

        PD_Adressen.loc[index,Ziele+"_Distanz"]=distanz
        PD_Adressen.loc[index,Ziele+"_Dauer"] = dauer

        print("")
        # F+r die API-Begrenzungen von openrouteservice. 40/min
        time.sleep(1.5)
        
        counter = counter+1

    #Zwischenspeichern
    if counter%5==0:
        print("Neu gespeichert.")
        PD_Adressen.to_csv("Gebiets_Adresse_"+Fortbewegung+".csv")
        PD_Adressen.to_excel("Gebiets_Adresse_"+Fortbewegung+".xlsx")


# Letztes Speichern
PD_Adressen.to_csv("Gebiets_Adresse_"+Fortbewegung+".csv")
PD_Adressen.to_excel("Gebiets_Adresse_"+Fortbewegung+".xlsx")