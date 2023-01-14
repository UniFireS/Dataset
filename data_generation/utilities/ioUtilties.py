import os
import shutil
import fiona
import json
from shapely import ops
from data_generation.utilities.geometryUtilities import getAreaOfPolygon
from data_generation.fireStructure import Fire
from shapely.geometry import mapping
from shapely.geometry import shape

# ------- writes fires to shapefiles
def storeFiresToSHP(fireList, folder, country, prefix="", suffix=""):
    if fireList == None: return
    if len(fireList) == 0: return
    if not os.path.exists(folder):
        os.makedirs(folder)
    schema = {"geometry" : "Polygon", "properties":{"id":"int", "startDate": "str", "endDate":"str", 
    "country":"str", "area_ha":"float", "area_acres":"float", 
    "land_cover":"int","fire_class":"str", "biome":"str", "burn_index":"str","on_fire_im":"int"}}
    shp = fiona.open(folder+prefix+country+suffix+".shp","w","ESRI Shapefile", schema, crs="EPSG:4326")

    for fire in fireList:
        lastFirePolygons = ops.unary_union(fire.firePolygons[fire.endDate])
        areaMeters = getAreaOfPolygon(lastFirePolygons)
        shp.write({"geometry":mapping(lastFirePolygons), "properties":{
        "id":fire.id, "startDate":fire.startDate, "endDate":fire.endDate, 
        "country":country,"area_acres":areaMeters* 0.000247105,"area_ha":areaMeters*1e-4,
        "land_cover":int(fire.landCover), "fire_class":chr(64+fire.getFireClass()), "biome":str(fire.biome), "burn_index":fire.maskType, "on_fire_im":fire.onFireDates}})
    shp.close()

def loadFiresFromSHP(filePath):
    if not os.path.exists(filePath):
        return None
    shp = fiona.open(filePath, "r")

    fireList = []
    for fire in shp:
        id = fire["properties"]["id"]
        startDate = fire["properties"]["startDate"]
        endDate = fire["properties"]["endDate"]
        country = fire["properties"]["country"]
        areaHA = fire["properties"]["area_ha"]
        areaA = fire["properties"]["area_acres"]
        landCover = fire["properties"]["land_cover"]
        biome = fire["properties"]["biome"] if "biome" in fire["properties"] else ""
        burn_index = fire["properties"]["burn_index"] if "burn_index" in fire["properties"] else ""
        on_fire_images = fire["properties"]["on_fire_im"] if "on_fire_im" in fire["properties"] else 0
        geometry = shape(fire["geometry"])
        newFire = Fire(id,startDate,endDate,areaA,areaHA,country)
        newFire.landCover = landCover
        newFire.biome = biome
        newFire.maskType = burn_index
        newFire.onFireDates = on_fire_images
        newFire.addFireDate(endDate,geometry)
        fireList.append(newFire)
    
    return fireList

def storePolygonsToSHP(polygons, folder, file):
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        schema = {"geometry": "Polygon"}
        shp = fiona.open(folder+file,"w","ESRI Shapefile",schema,crs="EPSG:4326")

        for poly in polygons:
            shp.write({"geometry":mapping(poly)})
        shp.close()

def storeJsonTimeStamps(file, timeStamDict):
    with open(file, "w") as fp:
        json.dump(timeStamDict, fp)

def loadJsonTimeStamps(file):
    return json.load(open(file))

def removeFolder(folder, reason):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    print(reason)
