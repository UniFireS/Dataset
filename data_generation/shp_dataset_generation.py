from datetime import timedelta
import glob
import json
import os
from affine import Affine
from matplotlib import pyplot
import numpy
from shapely.geometry import shape
from shapely import ops
import rasterio
import rasterio.mask
from datetime import datetime
import fiona
from data_generation.fireStructure import Fire
from data_generation.sentinel_downloader import getOptionalBands, requestData, searchAllDates, searchDate
from data_generation.utilities.ioUtilties import storeJsonTimeStamps, loadFiresFromSHP, removeFolder, storeFiresToSHP
from data_generation.utilities.pathUtilities import getBiomesFile,getCountryShapeFile, getJsonFireDateFolder, getLandCoverFolder, getRootFolder
from data_generation.utilities.geometryUtilities import getLargestIntersectingCountry,getBoundingBox,unified_bbox, maskToPolygons

# ------- Extracts all fires from shapefile for specific countries
def getFiresForCountry(firesFileName, countryFlags):
    sfFire = fiona.open(firesFileName)
    sfCountry = fiona.open(getCountryShapeFile())
    fireDictionary = {}
    countryPolygons = {}
    for i in sfCountry:
        if i["properties"]["POLYGON"] not in countryFlags:
            continue
        countryPolygons[i["properties"]["POLYGON"]] = shape(i["geometry"])

    counter = 0
    for i in sfFire:
        counter +=1
        print("processing entry " + str(counter) + " of " +
              str(len(sfFire)) + " in file " + firesFileName, end="\r")
        currentShape = shape(i["geometry"])
        currentRecords = i["properties"]

        if currentRecords["Id"] not in fireDictionary:
            fireDictionary[currentRecords["Id"]] = Fire(
                currentRecords["Id"], currentRecords["IDate"], currentRecords["FDate"])
        fireDictionary[currentRecords["Id"]].addFireDate(
            currentRecords["FDate"], currentShape)
    
    print("")
    counter = 0
    classFiresPerCountry = {}
    for country in countryFlags:
        classFiresPerCountry[country] = []
    
    for fire in fireDictionary:
        counter +=1
        print ("working through fire " + str(counter) + " of " + str(len(fireDictionary)), end ="\r")
        containerCountry = ""
        lastFirePolygon = fireDictionary[fire].firePolygons[fireDictionary[fire].endDate]
        containerCountry = getLargestIntersectingCountry(lastFirePolygon,countryPolygons)

        if containerCountry == "":
            continue

        fireDictionary[fire].country = containerCountry
        classFiresPerCountry[containerCountry].append(fireDictionary[fire])

    return classFiresPerCountry


def updateFireInfos(fires, doBiomes = False):
    if(len(fires)==0): return []
    update = 1
    output = []
    biomeSHP = fiona.open(getBiomesFile())
    country = fires[0].country

    countryBiomeShp = []
    for biome in biomeSHP:
        if biome["properties"]["POLYGON"] == country:
            countryBiomeShp.append(biome)

    with rasterio.open(getLandCoverFolder() + fires[0].country+"_LC100.tif") as landCovers:
        for fire in fires:
            print(f"Updating Fires {update}/{len(fires)}",end="\r")
            lastFirePolygon = fire.firePolygons[fire.endDate]
            landCoversImage, transform = rasterio.mask.mask(landCovers,lastFirePolygon,crop=True)
            values,counts = numpy.unique(landCoversImage[0],return_counts=True)
            mappedUniques = dict(zip(values,counts))

            currMax = 0
            currVal = 0
            for value in mappedUniques:
                if value == 255: continue
                if mappedUniques[value]>currMax:
                    currMax= mappedUniques[value]
                    currVal = value
            
            fire.landCover = currVal
            
            if not isinstance(lastFirePolygon, list):
                lastFirePolygon = [lastFirePolygon]
            
            lastFirePolygon = ops.unary_union(lastFirePolygon)

            if doBiomes:
                currMax = 0
                currVal = ""
                for biome in countryBiomeShp:
                    intersectionArea = lastFirePolygon.intersection(shape(biome["geometry"])).area
                    if intersectionArea>currMax:
                        currMax = intersectionArea
                        currVal = biome["properties"]["PADILLA"]

            fire.biome = currVal
            output.append(fire)
            update+=1
    
    return output
            

def filterFires(fires, minimumSizeClass = 1,hasAgricultural = False, naturalLandCover = 0, minimumLength=0 ):
    """Filters a list of fires based on several optional criterias:
    minimum Fire size, presence of agricultural land, % of natural land cover, minimum fire length
    the function assumes, that all fires are in the same country
    Parameters:
    fires: List of Fires
    minimumSizeClass: the minimum fire size (between 1-7)
    hasAgricultural: boolean for removing agricultural fires
    naturalLandCover: Percentage value of how much should be natural lands (between 0-100)
    minimumLength: Minimal fire duration in days"""
    filteredFires = []
    minimumSizeClass = max(1,min(minimumSizeClass,7))
    naturalLandCover = max(0,min(naturalLandCover,100))
    minimumLength = max(0,minimumLength)
    counter = 0
    with rasterio.open(getLandCoverFolder()+fires[0].country + "_LC100.tif") as landCoverMap:
        for fire in fires:
            counter+=1
            print(f"Filtering fire {counter} of {len(fires)}", end="\r")
            if fire.getFireClass() < minimumSizeClass: continue
            if fire.getFireDuration() < minimumLength: continue
            clipping, transform = rasterio.mask.mask(landCoverMap,fire.getLastFirePolygon(),crop=True)
            values,counts = numpy.unique(clipping[0],return_counts=True)
            mappedUniques = dict(zip(values,counts))
            if hasAgricultural:
                if 40 in mappedUniques: continue

            allGoodPixels = 0
            allNauralLandPixels = 0
            for uniqueValue in mappedUniques:
                if uniqueValue == 255: continue
                allGoodPixels += mappedUniques[uniqueValue]
                if uniqueValue in [114, 113, 123, 124, 111, 112, 121, 122, 115, 116, 125, 126]: 
                    allNauralLandPixels += mappedUniques[uniqueValue]
            if allGoodPixels == 0 : continue
            if allNauralLandPixels/allGoodPixels < naturalLandCover/100: continue
            filteredFires.append(fire)

    return filteredFires

def filterFiresExperimental(fires, minimumSizeClass = 1,hasAgricultural = False, naturalLandCover = 0, minimumLength=0 ):
    """Filters a list of fires based on several optional criterias:
    minimum Fire size, presence of agricultural land, % of natural land cover, minimum fire length
    the function assumes, that all fires are in the same country
    Parameters:
    fires: List of Fires
    minimumSizeClass: the minimum fire size (between 1-7)
    hasAgricultural: boolean for removing agricultural fires
    naturalLandCover: Percentage value of how much should be natural lands (between 0-100)
    minimumLength: Minimal fire duration in days"""
    filteredFires = []
    minimumSizeClass = max(1,min(minimumSizeClass,7))
    naturalLandCover = max(0,min(naturalLandCover,100))
    minimumLength = max(0,minimumLength)
    counter = 0
    with rasterio.open(getLandCoverFolder()+fires[0].country + "_LC100.tif") as landCoverMap:
        for fire in fires:
            counter+=1
            print(f"Filtering fire {counter} of {len(fires)}", end="\r")
            if fire.getFireClass() < minimumSizeClass: continue
            if fire.getFireDuration() < minimumLength: continue
            clipping, transform = rasterio.mask.mask(landCoverMap,fire.getLastFirePolygon(),crop=True)
            values,counts = numpy.unique(clipping[0],return_counts=True)
            mappedUniques = dict(zip(values,counts))
            if hasAgricultural:
                if 40 in mappedUniques: continue

            allGoodPixels = 0
            doNotAdd = True
            for uniqueValue in mappedUniques:
                if uniqueValue == 255: continue
                allGoodPixels += mappedUniques[uniqueValue]
            if allGoodPixels == 0 : continue

            for uniqueValue in mappedUniques:
                if uniqueValue in [114, 113, 123, 124, 111, 112, 121, 122, 115, 116, 125, 126]:
                    if mappedUniques[uniqueValue] / allGoodPixels > naturalLandCover/100: doNotAdd = False
            if not doNotAdd:
                filteredFires.append(fire)

    return filteredFires 


#------ Downloads all fires and stores them within country subfolder -- utilizes Unified_bbox function and transforms them to WGS84 at 512x512
def downloadFires(fires,firesTimeStamps ,rootFolder, country):
    postFireImages = 1
    preFireImages = 5
    onFireImages = 1
    downloadedImages = 0
    count = 0
    logFile = open(getRootFolder() + country + "_download_log.txt","a",buffering=1)
    for currentFire in fires:
        count+=1
        print(f"Downloading fire {count} of {len(fires)}")
        fireId = str(currentFire.id)
        fireEndDate = datetime.strptime(currentFire.endDate, "%Y-%m-%d")

        rootFolderAffix = country + "\\" + \
            str(fireEndDate.year)+"\\" + \
            str(fireEndDate.month) + "\\" + fireId+"\\"

        if os.path.exists(rootFolder+"Fire\\" +rootFolderAffix): continue    
        if fireId not in firesTimeStamps: continue
        if len(firesTimeStamps[fireId]["postFire"]) < postFireImages:continue
        if len(firesTimeStamps[fireId]["preFire"]) + len(firesTimeStamps[fireId]["onFire"]) < preFireImages:continue
        if len(firesTimeStamps[fireId]["onFire"])<onFireImages:continue

        endPolygons = currentFire.firePolygons[currentFire.endDate]
        boundingBoxFire = getBoundingBox(endPolygons)
        fireBB, nonFireBB = unified_bbox(boundingBoxFire)

        downloadedImages += downloadImageSet(firesTimeStamps[fireId], 
        1,5,1,1, fireBB, 
        rootFolder+"Fire\\" + rootFolderAffix, currentFire.id)
        #downloadImageSet(5,1,fireEndDate,nonFireBB,rootFolder+"NoFire\\" + rootFolderAffix)
        logFile.write(f"Processed fire {currentFire.id} \n")
    logFile.close()
    return downloadedImages

def sortBasedOnOnFire(fires, timestamps):
    matchedOnFiresList = []
    for fire in fires:
        if str(fire.id) not in timestamps:
            matchedOnFiresList.append(-1)
        else:
            matchedOnFiresList.append(len(timestamps[str(fire.id)]["onFire"]))
    
    return [x for _, x in sorted(zip(matchedOnFiresList,fires))]

def downloadImageSet(timestamps, minPostFire, maxPreFires,minNoFire ,minOnFire,bbox, folder, fireId):
    sceneNoDataCoverage = 0.3
    sceneCloudCoverage = 0.1

    onFireDownloads = 0
    preFireDownloads = 0
    postFireDownloads = 0

    preFireDates = []
    postfireDates = []

    if not os.path.exists(folder):
        os.makedirs(folder)

    ## On Fire downloads
    for timestampTuple in reversed(timestamps["onFire"]):
        scl = getOptionalBands([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
        timestampTuple["start"],
        timestampTuple["end"])

        sclNoData= (scl==0).sum()
        sclCloudCoverage = (scl==8).sum() + (scl==9).sum()
        sclPixels = scl.size

        if sclNoData <sceneNoDataCoverage* sclPixels and sclCloudCoverage<sceneCloudCoverage*sclPixels:
                numpy.save(folder+"scl_"+timestampTuple["start"]+".npy",scl)
                onFireDownloads +=1
                preFireDates.append(timestampTuple)
        
        if onFireDownloads >= maxPreFires - minNoFire:
            break
    # Remove folder if not enough in fire images have been found
    if onFireDownloads < minOnFire:
        removeFolder(folder,f"Fire {fireId} skipped due to not enough on fire image")
        return False
    ## Pre Fire Downloads
    for timestampTuple in timestamps["preFire"]:
        if onFireDownloads+preFireDownloads >= maxPreFires:
            break
        scl = getOptionalBands([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
        timestampTuple["start"],
        timestampTuple["end"])

        sclNoData= (scl==0).sum()
        sclCloudCoverage = (scl==8).sum() + (scl==9).sum()
        sclPixels = scl.size

        if sclNoData <sceneNoDataCoverage* sclPixels and sclCloudCoverage<sceneCloudCoverage*sclPixels:
                numpy.save(folder+"scl_"+timestampTuple["start"]+".npy",scl)
                preFireDownloads +=1
                preFireDates.append(timestampTuple)
    
    #Remove folder if not enough pre fire images have been found (total)
    if onFireDownloads + preFireDownloads< maxPreFires:
        removeFolder(folder, f"Fire {fireId} skipped due to not enough pre fire images")
        return False

    ## Post Fire Downloads
    for timestampTuple in reversed(timestamps["postFire"]):
        scl = getOptionalBands([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
        timestampTuple["start"],
        timestampTuple["end"])

        sclNoData= (scl==0).sum()
        sclCloudCoverage = (scl==8).sum() + (scl==9).sum()
        sclPixels = scl.size

        if sclNoData <sceneNoDataCoverage* sclPixels and sclCloudCoverage<sceneCloudCoverage*sclPixels:
                numpy.save(folder+"scl_"+timestampTuple["start"]+".npy",scl)
                postFireDownloads +=1
                postfireDates.append(timestampTuple)
        
        if postFireDownloads >= minPostFire:
            break
    
    if postFireDownloads < minPostFire:
        removeFolder(folder, f"Fire {fireId} skipped due to not enough post fire images")
        return False

    for timestampTuple in preFireDates:
        requestData([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
        timestampTuple["start"],
        timestampTuple["end"],
        folder, "pre_fire")
    
    for timestampTuple in postfireDates:
        requestData([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
        timestampTuple["start"],
        timestampTuple["end"],
        folder, "post_fire")
    
    return True



 
def getFireTimestampsSHub(endDate, startDate, bbox, tileCloudCoverage):
    if not isinstance(endDate, datetime):
        endDate = datetime.strptime(endDate, "%Y-%m-%d")
    
    if not isinstance(startDate, datetime):
        startDate = datetime.strptime(startDate, "%Y-%m-%d")

    preFireDates =[]
    onFireDates = []
    postFireDates = []

    allValiDates = searchAllDates([bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],endDate+timedelta(days=-120),endDate+timedelta(days=40),tileCloudCoverage)
    if allValiDates is None: return None
    for validDate in allValiDates:
        if datetime.strptime(validDate,"%Y-%m-%d") < startDate:
            preFireDates.append((validDate,validDate))
        if datetime.strptime(validDate,"%Y-%m-%d") >= startDate and datetime.strptime(validDate,"%Y-%m-%d")<=endDate:
            onFireDates.append((validDate,validDate))
        if datetime.strptime(validDate,"%Y-%m-%d")>endDate:
            postFireDates.append((validDate,validDate))


    fireDateDictionary = {
        "preFire":[],
        "onFire":[],
        "postFire":[]
    }
    for preFireDateTuple in preFireDates:
        fireDateDictionary["preFire"].append({"start":preFireDateTuple[0],"end":preFireDateTuple[1]})
    
    for onFireDateTuple in onFireDates:
        fireDateDictionary["onFire"].append({"start":onFireDateTuple[0],"end":onFireDateTuple[1]})

    for postFireDateTuple in postFireDates:
        fireDateDictionary["postFire"].append({"start":postFireDateTuple[0],"end":postFireDateTuple[1]})
    
    return fireDateDictionary


def improveFirePolygons(filteredModisRootFolder, maskRootFolder, maskIdentifier,outputFolder ,inputShapePrefix ="", inputShapeSuffix = "", outputShapePrefix = "", outputShapeSuffix="",countries=None):
    if countries == None:
        countries = glob.glob(maskRootFolder+"*")
    else:
        countries = [maskRootFolder+x for x in countries]
    
    for i,country in enumerate(countries):
        cFlag = country.split("\\")[-1]
        countryFires = loadFiresFromSHP(filteredModisRootFolder + inputShapePrefix + cFlag +inputShapeSuffix+ ".shp")
        countryRootFolder = country + "\\**\\"

        modifiedFires = []
        print(f"Processing country {i+1} of {len(countries)}.",end="\r")
        for fireMaskPath in glob.glob(countryRootFolder+"*"+maskIdentifier+"*.png",recursive=True):
            fireMaskId = fireMaskPath.split("\\")[-2]
            mask_identifier = os.path.basename(fireMaskPath).split("_")[0][1:]
            dir_name = os.path.dirname(fireMaskPath)
            fireMask = pyplot.imread(fireMaskPath)[:,:,0]
            fireTransform = json.load(open(glob.glob("\\".join(fireMaskPath.split("\\")[0:-1])+"\\*.json")[0]))
            transform = Affine(fireTransform["a"],fireTransform["b"],fireTransform["c"],fireTransform["d"],fireTransform["e"],fireTransform["f"])
            firePolygons = maskToPolygons(fireMask,fireMask>0 ,transform)

            if len(firePolygons)==0: continue

            fire = list(filter(lambda x: str(x.id) == fireMaskId, countryFires))
            if fire == []:
                print(f"Fire with Id: {fireMaskId} in country {country} was not found")
                continue
            fire = fire[0] 
            fire.firePolygons = {}
            for firePolygon in firePolygons:
                fire.addFireDate(fire.endDate, firePolygon)
            fire.maskType = mask_identifier
            
            #get on fire number
            preFires = glob.glob(dir_name+"//pre_fire_*.npy")
            onFireCount = 0
            for preFireName in preFires:
                pre_fire_name_date = os.path.basename(preFireName).split("_")[2][:-4]
                if pre_fire_name_date >= fire.startDate:
                    onFireCount += 1
            fire.onFireDates = onFireCount

            modifiedFires.append(fire)
        
        storeFiresToSHP(modifiedFires,outputFolder,cFlag,outputShapePrefix,outputShapeSuffix)