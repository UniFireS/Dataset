import enum
import random
import pyproj
from matplotlib import pyplot
from sentinelhub import CRS, BBox
from shapely.geometry import Polygon, Point
from shapely.affinity import affine_transform
from shapely.geometry import mapping
from data_generation.preprocessing import generateDataSet
from data_generation.utilities.imageUtilities import *
from data_generation.utilities.ioUtilties import loadJsonTimeStamps
from data_generation.utilities.pathUtilities import get_erc_folder, get_gmt_file, getAllPathsToImagery, getERA5Folder, getMODISFolder, getRootFolder, getFWIFolder
from data_generation.utilities.ioUtilties import loadFiresFromSHP, storeFiresToSHP
from data_generation.shp_dataset_generation import *
import glob
import os
import shutil
import numpy
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from dateutil.relativedelta import relativedelta
import csv
from rasterio.features import rasterize

#-------- GWIS/MODIS Download, Save Country into ShapeFiles, Download S2 Imagery-----

#"Cameroon", "United Republic of Tanzania"
countries = ["United Republic of Tanzania"]

def recomupteMasks():
        counter = 0
        shp_file = fiona.open("E:\\EFFIS_Validation\\joint_EFFIS_THESIS.shp")
        for fp in os.listdir("E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR"):
                counter += 1
                fireId = fp
                folderPath = "E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR\\" +fp + "\\"
                startDate = list(filter(lambda x: str(x["properties"]["id"]) == fireId,shp_file))[0]["properties"]["initialdat"]

                print (f"Generating Mask for fire {counter} of {len(folderPath)}",end="\r")
                postFirePaths = glob.glob(folderPath+"post_fire_*.npy")
                preFiresPaths = glob.glob(folderPath+"pre_fire_*.npy")
                
                if len(postFirePaths)== 0 or len(preFiresPaths)==0:
                        shutil.rmtree(folderPath)
                        continue

                postFireDate = datetime.strptime(postFirePaths[0].split("_")[-1].split(".")[0],"%Y-%m-%d")
                preFireDates = sorted([datetime.strptime(x.split("_")[-1].split(".")[0], "%Y-%m-%d") for x in preFiresPaths])
                startDate = datetime.strptime(startDate, "%Y-%m-%d")
                if sum(map(lambda x: x <= startDate, preFireDates))==5:
                        preFireDate = preFireDates[4]
                elif sum(map(lambda x: x >= startDate, preFireDates))==5:
                        preFireDate = preFireDates[0]
                else:
                        preFireDate = sorted(filter(lambda x: x<startDate,preFireDates))[-1]

                postFireNumpy = numpy.load(folderPath + "post_fire_" + datetime.strftime(postFireDate, "%Y-%m-%d") + ".npy").astype(int)
                preFireNumpy = numpy.load(folderPath + "pre_fire_" + datetime.strftime(preFireDate, "%Y-%m-%d") +".npy").astype(int)
                preFireSCL = numpy.load(folderPath + "scl_" + datetime.strftime(preFireDate, "%Y-%m-%d") + ".npy").astype(int)
                postFireSCL = numpy.load(folderPath + "scl_" + datetime.strftime(postFireDate, "%Y-%m-%d") + ".npy").astype(int)
                preMask =  computeSCLMask(preFireSCL) + computeNDWIMask(preFireNumpy)  
                postMask =  computeSCLMask(postFireSCL)  +  computeNDWIMask(postFireNumpy)

                rdnbr, rbr, dnbr = computeFireMasks(preMask, postMask, preFireNumpy, postFireNumpy)
                if os.path.exists(folderPath + "dNBR.png"):
                        storeDNBR(dnbr, folderPath + "dNBR.png")

                        dnbr = createBinaryImage(dnbr,0.27)
                        writeBinaryFile(dnbr,folderPath+"dNBR_binary.png")


                        dnbr_step1 = removeSmallContours(dnbr,450)
                        dnbr_step2 = removeNoise(dnbr_step1,iterationSteps=2, structType="circle")
                        dnbr_step3 = fillContours(dnbr_step2,75)
              
                        writeBinaryFile(dnbr_step3,folderPath+"2dNBR_final_mask.png")

                        if (dnbr_step3>0).sum() <= 0:
                                shutil.rmtree(folderPath)      
                                continue

                elif os.path.exists(folderPath + "RBR.png"):
                        storeDNBR(rbr, folderPath + "RBR.png")

                        rbr = createBinaryImage(rbr,0.27)
                        writeBinaryFile(rbr,folderPath+"RBR_Binary.png")

                        rbr_step1 = removeSmallContours(rbr,450)
                        rbr_step2 = removeNoise(rbr_step1,iterationSteps=2, structType="circle")
                        rbr_step3 = fillContours(rbr_step2,75)
            
                        writeBinaryFile(rbr_step3,folderPath+"3RBR_final_mask.png")
                        if (rbr_step3>0).sum() <= 0:
                                shutil.rmtree(folderPath)      
                                continue

                elif os.path.exists(folderPath + "RdNBR.png"):
                        storeDNBR(rdnbr, folderPath + "RdNBR.png")

                        rdnbr = createBinaryImage(rdnbr,0.27)
                        writeBinaryFile(rdnbr,folderPath+"RdNBR_binary.png")
                        rdnbr_step1 = removeSmallContours(rdnbr,450)
                        rdnbr_step2 = removeNoise(rdnbr_step1,iterationSteps=2, structType="circle")
                        rdnbr_step3 = fillContours(rdnbr_step2,75)

                        writeBinaryFile(rdnbr_step3,folderPath+"4RdNBR_final_mask.png")
                        if (rdnbr_step3>0).sum() <= 50:
                                shutil.rmtree(folderPath)      
                                continue

def generateMasks():
        counter = 0
        firesPerCountry = {}
        allPaths = getAllPathsToImagery("E:\\Thesis_imagery\\",["Good_Fires"], ["Colombia"])
        for folderPath in allPaths:
                counter += 1
                fireId = folderPath.split("\\")[-2]
                country = folderPath.split("\\")[-5]
                if country not in firesPerCountry:
                        firesPerCountry[country] = loadFiresFromSHP(getRootFolder()+"Polygons_GlobFire_CALC\\GlobFire_" + country + "_CALC.shp")
                fire = next(filter(lambda x: str(x.id)==fireId, firesPerCountry[country]))

                print (f"Generating Mask for fire {counter} of {len(allPaths)}",end="\r")
                postFirePaths = glob.glob(folderPath+"post_fire_*.npy")
                preFiresPaths = glob.glob(folderPath+"pre_fire_*.npy")
                
                if len(postFirePaths)== 0 or len(preFiresPaths)==0:
                        shutil.rmtree(folderPath)
                        continue

                postFireDate = datetime.strptime(postFirePaths[0].split("_")[-1].split(".")[0],"%Y-%m-%d")
                preFireDates = sorted([datetime.strptime(x.split("_")[-1].split(".")[0], "%Y-%m-%d") for x in preFiresPaths])
                startDate = datetime.strptime(fire.startDate, "%Y-%m-%d")
                if sum(map(lambda x: x <= startDate, preFireDates))==5:
                        preFireDate = preFireDates[4]
                elif sum(map(lambda x: x >= startDate, preFireDates))==5:
                        preFireDate = preFireDates[0]
                else:
                        preFireDate = sorted(filter(lambda x: x<startDate,preFireDates))[-1]

                preFireDate = preFireDates[0] #TODO:: Remove after done with recomputations

                postFireNumpy = numpy.load(folderPath + "post_fire_" + datetime.strftime(postFireDate, "%Y-%m-%d") + ".npy").astype(int)
                preFireNumpy = numpy.load(folderPath + "pre_fire_" + datetime.strftime(preFireDate, "%Y-%m-%d") +".npy").astype(int)

                preFireSCL = numpy.load(folderPath + "scl_" + datetime.strftime(preFireDate, "%Y-%m-%d") + ".npy").astype(int)
                postFireSCL = numpy.load(folderPath + "scl_" + datetime.strftime(postFireDate, "%Y-%m-%d") + ".npy").astype(int)
               
               
                preMask =  computeSCLMask(preFireSCL) + computeNDWIMask(preFireNumpy)  
                postMask =  computeSCLMask(postFireSCL)  +  computeNDWIMask(postFireNumpy)


                rdnbr, rbr, dnbr = computeFireMasks(preMask, postMask, preFireNumpy, postFireNumpy)
# ------------------dnbr                                       
                storeDNBR(dnbr, folderPath + "dNBR.png")

                dnbr = createBinaryImage(dnbr,0.27)
                dnbr_step1 = removeSmallContours(dnbr,450)
                dnbr_step2 = removeNoise(dnbr_step1,iterationSteps=2, structType="circle")
                dnbr_step3 = fillContours(dnbr_step2,75)

                writeBinaryFile(dnbr_step3,folderPath+"2dNBR_final_mask.png")

                if (dnbr_step3>0).sum() == 0:
                        shutil.rmtree(folderPath)      
                        continue

# # # # ------------------rbr
                storeDNBR(rbr, folderPath + "RBR.png")

                rbr = createBinaryImage(rbr,0.27)
                rbr_step1 = removeSmallContours(rbr,450)
                rbr_step2 = removeNoise(rbr_step1,iterationSteps=2, structType="circle")
                rbr_step3 = fillContours(rbr_step2,75)

                writeBinaryFile(rbr_step1,folderPath+"3RBR_final_mask.png")
                if (rbr_step3>0).sum() == 0:
                        shutil.rmtree(folderPath)      
                        continue

# # ------------------RnDBR
                storeDNBR(rdnbr, folderPath + "RdNBR.png")

                rdnbr = createBinaryImage(rdnbr,0.27)
                rdnbr_step1 = removeSmallContours(rdnbr,450)
                rdnbr_step2 = removeNoise(rdnbr_step1,iterationSteps=2, structType="circle")
                rdnbr_step3 = fillContours(rdnbr_step2,75)

                writeBinaryFile(rdnbr_step3,folderPath+"4RdNBR_final_mask.png")
                if (rdnbr_step3>0).sum() == 0:
                        shutil.rmtree(folderPath)      
                        continue

                FalseImage_preFire = numpy.clip(preFireNumpy[:,:,[7,3,2]]/10000*3.5,0,1)
                FalseImage_postFire = numpy.clip(postFireNumpy[:,:,[7,3,2]]/10000*3.5,0,1)
                pyplot.imsave(folderPath+"1_FalseImage_False_RGBColor_post.png", FalseImage_postFire)
                pyplot.imsave(folderPath+"0_FalseImage_False_RGBColor_pre.png", FalseImage_preFire)


def processShapeFiles():
        totalFires = {}
        for country in countries:
                totalFires[country] = []

        for file in glob.glob(getMODISFolder()+"*.shp"):
                fires = getFiresForCountry(file, countries)
                print("")
                for country in countries:
                        totalFires[country] += fires[country]
                        print(country + " " + str(len(totalFires[country])))
        
        for country in countries:
                storeFiresToSHP(totalFires[country],getRootFolder() + "Polygons_GlobFire_CA\\",country,"GlobFire_","_CA")

def generateTimeStamps():
        if not os.path.exists(getJsonFireDateFolder()):
                os.makedirs(getJsonFireDateFolder())
        for country in countries:
                print(f"Generating Timestamps for {country}")
                fires = loadFiresFromSHP(getRootFolder()+ "Polygons_GlobFire_CALC\\GlobFire_" + country + "_CALC.shp")
                if fires is None:
                        print(f"{country} has no filtered fires at all!")
                        continue
                jsonObject = {}
                for i, fire in enumerate(fires):
                        print(f"Processing fire {i+1} of {len(fires)}", end="\r")
                        dates = getFireTimestampsSHub(fire.endDate,fire.startDate, unified_bbox(getBoundingBox(fire.getLastFirePolygon()))[0] ,30)
                        if dates is None: continue
                        jsonObject[fire.id]= dates
                storeJsonTimeStamps(getJsonFireDateFolder()+country+".json",jsonObject)

                jsonFires = loadJsonTimeStamps(getJsonFireDateFolder() + country +".json")

                counter = 0
                for fire in jsonFires:
                        if jsonFires[fire] is None: continue
                        if len(jsonFires[fire]["postFire"]) < 1:continue
                        if len(jsonFires[fire]["preFire"]) + len(jsonFires[fire]["onFire"]) < 5:continue
                        if len(jsonFires[fire]["onFire"])<1:continue
                        counter +=1

                print (f"{country} has {counter} potential fires") 

def download(firePerCountry):   # Step 3
    for country in countries:
        logFile = open(getRootFolder() + country+"_download_log.txt", "w")
        logFile.close()
        print(f"Downloading {firePerCountry} images for {country}")
        fires = loadFiresFromSHP(
            getRootFolder() + "Polygons_GlobFire_CALC\\GlobFire_" + country + "_CALC.shp")
        timeStamps = loadJsonTimeStamps(
            getJsonFireDateFolder() + country + ".json")
        sortedFires = sortBasedOnOnFire(fires, timeStamps)
        successfulDownloads = 0
        while (successfulDownloads < firePerCountry):
            if len(sortedFires) <= firePerCountry - successfulDownloads:
                downloadFires(sortedFires, timeStamps,
                              "E:\\ModisImage\\Additional_Downloads\\", country)
                break
            firesToDownload = sortedFires[-(firePerCountry -
                                            successfulDownloads):]
            successfulDownloads += downloadFires(
                firesToDownload, timeStamps, "E:\\ModisImage\\Additional_Downloads\\", country)
            fireToDownloadIds = list(map(lambda x: x.id, firesToDownload))
            sortedFires = [
                x for x in sortedFires if x.id not in fireToDownloadIds]
        print(f"Downloaded {successfulDownloads} fires for {country}")

def filterAndUpdateShapeFiles():
        for country in countries: 
                print(f"Filtering fires for {country}")
                fires = loadFiresFromSHP(getRootFolder()+ "Polygons_GlobFire_CA\\GlobFire_" + country + "_CA.shp")
                if fires is None:
                        print(f"{country} has no fires at all!")
                        continue
                filteredFires = filterFires(fires,5,True,51)
                print(f"Updating fires with land cover for {country}")
                updatedFires = updateFireInfos(filteredFires)
                storeFiresToSHP(updatedFires,getRootFolder()+ "Polygons_GlobFire_CALC\\",country,"GlobFire_","_CALC")

def checkForStranglers(rootFolder):
        allFires = getAllPathsToImagery(rootFolder,["Fire_Masks"],countries)

        for fire in allFires:
                if len(glob.glob(fire + "*_final_mask.png")) > 1:
                        print (f"Fire at {fire} has too many masks")
                if len(glob.glob(fire + "post_fire_*.npy")) > 1:
                        print(f"Fire at {fire} has too many post fires")
                if len(glob.glob(fire + "pre_fire_*.npy")) > 5:
                        print(f"Fire at {fire} has too many pre fires")

def filterFiresForPacking(paths, **kwargs):
        filtered_fires = []
        fire_per_country= {}
        for i,fire_path in enumerate(paths):
                print(f"Filtering fire {i+1} of {len(paths)}", end="\r")
                fire_id = fire_path.split("\\")[-2]
                country = fire_path.split("\\")[-5]
                if country not in fire_per_country:
                        fire_per_country[country] = loadFiresFromSHP(getRootFolder()+"Polygons_Thesis_Results\\Version_4_Biomes_Filtered\\Thesis_" + country + "_CALCBMIB.shp")
                fire = list(filter(lambda x: str(x.id)==fire_id, fire_per_country[country]))
                if fire == []: continue
                fire = fire[0]
                requirements = 0
                if "landcover" in kwargs:
                        with rasterio.open(getLandCoverFolder()+country + "_LC100.tif") as landCoverMap:
                                clipping, _ = rasterio.mask.mask(landCoverMap,fire.getLastFirePolygon(),crop=True)
                                values,counts = numpy.unique(clipping[0],return_counts=True)
                                mappedUniques = dict(zip(values,counts))
                                allGoodPixels = 0
                                allNauralLandPixels = 0
                                for uniqueValue in mappedUniques:
                                        if uniqueValue == 255: continue
                                        allGoodPixels += mappedUniques[uniqueValue]
                                        if uniqueValue in [114, 113, 123, 124, 111, 112, 121, 122, 115, 116, 125, 126]: 
                                                allNauralLandPixels += mappedUniques[uniqueValue]
                                if allGoodPixels>0 and allNauralLandPixels/allGoodPixels >= kwargs["landcover"]/100:
                                        requirements+=1
                if "biome" in kwargs:
                        biomes = kwargs["biome"]
                        if type(biomes) != list:
                                biomes = [biomes]
                        if fire.biome in biomes:
                                requirements+=1 
                if "onFire" in kwargs:
                        if fire.onFireDates == kwargs["onFire"]:
                                requirements+=1
                if "temporalCohesion" in kwargs:
                        if kwargs["temporalCohesion"] == True:
                                post_fire_paths = glob.glob(fire_path+"post_fire_*.npy")
                                pre_fires_paths = glob.glob(fire_path+"pre_fire_*.npy")

                                post_fire_date = datetime.strptime(post_fire_paths[0].split("_")[-1].split(".")[0],"%Y-%m-%d")
                                pre_fire_dates = sorted([datetime.strptime(x.split("_")[-1].split(".")[0], "%Y-%m-%d") for x in pre_fires_paths])

                                is_coherent = True
                                temporal_step = (pre_fire_dates[1]-pre_fire_dates[0]).days
                                for i, pre_fire_date in enumerate(pre_fire_dates):
                                        if i == 0: continue
                                        if i == len(pre_fire_dates)-1: next_fire = post_fire_date
                                        else: next_fire = pre_fire_dates[i+1]

                                        if (next_fire - pre_fire_date).days != temporal_step: is_coherent = False
                                if is_coherent: requirements +=1
                if "maxOnFire" in kwargs:
                        if fire.onFireDates <= kwargs["maxOnFire"]:
                                requirements+=1
                if "dominantLandcover" in kwargs:
                        dominant_list = kwargs["dominantLandcover"]
                        if type(dominant_list) != list:
                                dominant_list = [dominant_list]
                        if fire.landCover in dominant_list:
                                requirements += 1
                if "fireSize" in kwargs:
                        fireSize_list = kwargs["fireSize"]
                        if type(fireSize_list) != list:
                                fireSize_list = [fireSize_list]
                        if fire.getFireClass() in fireSize_list:
                                requirements +=1
                
                if requirements == len(kwargs): filtered_fires.append(fire_path)
        
        return filtered_fires
                
def generate_raster_data(paths, use_fwi = False,use_era5 = False, use_nbr=False,use_landcover=False, use_erc = False, use_gmt = False, use_latlong = False):
        era_label_value = {"2m_dewpoint_temperature":"mean","2m_temperature":"mean",
                           "10m_u_component_of_wind":"mean","10m_v_component_of_wind":"mean",
                            "total_precipitation":"sum"}
        for i,folderPath in enumerate(paths):
                print(f"Generating raster data for image {i+1} of {len(paths)}", end="\r")
                country = folderPath.split("\\")[-5]

                postFirePaths = glob.glob(folderPath+"post_fire_*.npy")
                preFiresPaths = glob.glob(folderPath+"pre_fire_*.npy")
                all_fire_paths= numpy.concatenate((preFiresPaths,postFirePaths))
                postFireDate = datetime.strptime(postFirePaths[0].split("_")[-1].split(".")[0],"%Y-%m-%d")
                preFireDates = sorted([datetime.strptime(x.split("_")[-1].split(".")[0], "%Y-%m-%d") for x in preFiresPaths])
                
                FWIPostDate = datetime.strftime(postFireDate, "%Y%m%d")
                FWIPreDates = [datetime.strftime(x, "%Y%m%d") for x in preFireDates]
                FWIAllDates = numpy.concatenate((FWIPreDates,[FWIPostDate])) 

                eraPostPath = datetime.strftime(postFireDate,"\\%Y\\%m\\%d\\")
                eraPrePaths = [datetime.strftime(x, "\\%Y\\%m\\%d\\") for x in preFireDates]
                era_all_paths = numpy.concatenate((eraPrePaths,[eraPostPath]))

                ercPostDate = datetime.strftime(postFireDate,"%Y%m%d")
                ercPreDates = [datetime.strftime(x, "%Y%m%d") for x in preFireDates] 
                ercAllDates = numpy.concatenate((ercPreDates,[ercPostDate]))
             
                fireTransform = json.load(open(glob.glob(folderPath + "*.json")[0]))
                transform = Affine(fireTransform["a"],fireTransform["b"],fireTransform["c"],fireTransform["d"],fireTransform["e"],fireTransform["f"])

                boundingBox = Polygon([(0,0),(0,512),(512,512),(512,0)])
                boundingBox = affine_transform(boundingBox,transform.to_shapely())

                if use_fwi:
                        for i,fwiDate in enumerate(FWIAllDates):
                                date = all_fire_paths[i].split("_")[-1].split(".")[0]
                                if os.path.exists(folderPath + "fwi_" + date+ ".npy"): continue
                                upscaled_clipping = clip_and_scale(getFWIFolder() + f"ECMWF_FWI_FWI_{fwiDate}_1200_hr_v4.tiff",boundingBox,512,512)
                                numpy.save(folderPath + "fwi_" + date+ ".npy",upscaled_clipping)
                if use_era5:
                        for i,eraPath in enumerate(era_all_paths):
                                date = all_fire_paths[i].split("_")[-1].split(".")[0]
                                if os.path.exists(folderPath + f"humidity_{date}.npy") and os.path.exists(folderPath + f"precipitation_{date}.npy") and os.path.exists(folderPath + f"wind_{date}.npy"): continue
                                dewpoint_image = clip_and_scale(getERA5Folder() + "2m_dewpoint_temperature" + eraPath + era_label_value["2m_dewpoint_temperature"] + ".tiff",boundingBox,512,512)
                                temperature_image = clip_and_scale(getERA5Folder() + "2m_temperature" + eraPath + era_label_value["2m_temperature"] + ".tiff",boundingBox,512,512)
                                u_wind_image = clip_and_scale(getERA5Folder() + "10m_u_component_of_wind" + eraPath + era_label_value["10m_u_component_of_wind"] + ".tiff",boundingBox,512,512)
                                v_wind_image = clip_and_scale(getERA5Folder() + "10m_v_component_of_wind" + eraPath + era_label_value["10m_v_component_of_wind"] + ".tiff",boundingBox,512,512)
                                percipitation_image = clip_and_scale(getERA5Folder() + "total_precipitation" + eraPath + era_label_value["total_precipitation"] + ".tiff",boundingBox,512,512)

                                humidity_image = 100*numpy.power((112-0.1*temperature_image+dewpoint_image)/(112+0.9*temperature_image),numpy.ones_like(temperature_image)*8)
                                wind_image = numpy.sqrt(numpy.power(u_wind_image,numpy.ones_like(u_wind_image)*2) + numpy.power(v_wind_image,numpy.ones_like(v_wind_image)*2))

                                numpy.save(folderPath + f"humidity_{date}.npy",humidity_image)
                                numpy.save(folderPath + f"precipitation_{date}.npy",percipitation_image)
                                numpy.save(folderPath + f"wind_{date}.npy",wind_image)
                if use_landcover:
                        if len(glob.glob(folderPath+"lc_*")) == 6: continue
                        upscaled_clipping = clip_and_scale(getLandCoverFolder() + country+"_LC100.tif",boundingBox,512,512)
                        for fire_path in all_fire_paths:
                                date = fire_path.split("_")[-1].split(".")[0]
                                numpy.save(folderPath + "lc_" + date + ".npy",upscaled_clipping)
                if use_nbr:
                        for fire_path in all_fire_paths:
                                date = fire_path.split("_")[-1].split(".")[0]
                                if os.path.exists(folderPath + f"nbr_{date}.npy"): continue
                                image = numpy.load(fire_path).astype("int32")
                                ndvi = compute_nbr(image)
                                numpy.save(folderPath + f"nbr_{date}.npy",ndvi)
                if use_erc:
                        for i,erc_date in enumerate(ercAllDates):
                                date = all_fire_paths[i].split("_")[-1].split(".")[0]
                                if os.path.exists(folderPath + f"erc_{date}.npy"): continue
                                erc_image = clip_and_scale(get_erc_folder() + f"ECMWF_NFDRS_ERC_{erc_date}_1200_hr_v4.tiff", boundingBox, 512,512)
                                numpy.save(folderPath + f"erc_{date}.npy",erc_image)
                if use_gmt:
                        if len(glob.glob(folderPath + "gmt_*")) == 6: continue
                        clipping = clip_and_scale(get_gmt_file(),boundingBox,512,512)
                        for fire_path in all_fire_paths:
                                date = fire_path.split("_")[-1].split(".")[0]
                                numpy.save(folderPath + "gmt_" + date + ".npy",clipping)
                if use_latlong:
                        if len(glob.glob(folderPath+"latitude_*")) == 6 and \
                                len(glob.glob(folderPath+"longitude_*")) == 6: continue
                        latitude = numpy.zeros((1,512,512))
                        longitude = numpy.zeros((1,512,512))
                        for x in range(512):
                                for y in range(512):
                                        xy_point = Point(x,y)
                                        xy_point_transformed = affine_transform(xy_point , transform.to_shapely())
                                        latitude[0,y,:] = xy_point_transformed.y
                                        longitude[0,:,x] = xy_point_transformed.x
                        
                        for fire_path in all_fire_paths:
                                date = fire_path.split("_")[-1].split(".")[0]
                                numpy.save(folderPath + "latitude_" + date + ".npy",latitude)
                                numpy.save(folderPath + "longitude_" + date + ".npy",longitude)





def processEFFISFires(rootFolder, rootOutput):
        
        output_schema = {"geometry":"Polygon","properties":{
                "id":"int","initialdat":"str","finaldate":"str","area_ha":"int","area_acres":"int","land_cover":"int","fire_class":"str"
        }}
        allShpPaths = glob.glob(rootFolder+"*.shp")
        for shpPath in allShpPaths:
                countryFlag = shpPath.split("\\")[-1].split(".")[0].split("_")[-1]
                landCoverFile = rasterio.open(getLandCoverFolder() + countryFlag + "_LC100.tif")
                shp = fiona.open(shpPath, "r")
                shp_output = fiona.open(rootOutput + "EFFIS_" + countryFlag+"_CALC.shp","w","ESRI Shapefile",output_schema,"EPSG:4326")
                for fire in shp:
                        id = fire["properties"]["id"]
                        startDate = fire["properties"]["initialdat"]
                        endDate = fire["properties"]["finaldate"]
                        areaHA = fire["properties"]["area_ha"]
                        geometry = shape(fire["geometry"])
                        areaAcres = areaHA*2.47105
                        if areaAcres<300: continue
                        fireClass = 0
                        if areaAcres < 1000: fireClass=5
                        elif areaAcres<5000:fireClass = 6
                        else: fireClass = 7
                        clipping, _ = rasterio.mask.mask(landCoverFile,[geometry],crop=True)
                        values,counts = numpy.unique(clipping[0],return_counts=True)
                        mappedUniques = dict(zip(values,counts))
                        if 40 in mappedUniques: continue

                        allGoodPixels = 0
                        allNauralLandPixels = 0
                        currVal = 0
                        currMax = 0 
                        for uniqueValue in mappedUniques:
                                if uniqueValue == 255: continue
                                allGoodPixels += mappedUniques[uniqueValue]
                                if uniqueValue in [114, 113, 123, 124, 111, 112, 121, 122, 115, 116, 125, 126]: 
                                        allNauralLandPixels += mappedUniques[uniqueValue]
                                if mappedUniques[uniqueValue]>currMax:
                                        currMax= mappedUniques[uniqueValue]
                                        currVal = uniqueValue
                        if allGoodPixels == 0 : continue
                        if allNauralLandPixels/allGoodPixels < 0.51: continue

                        shp_output.write({"geometry":mapping(geometry),
                                        "properties":{
                                                "id":id, "initialdat":startDate, "finaldate":endDate, "area_ha":areaHA, "area_acres":int(areaAcres),
                                                "land_cover":int(currVal),"fire_class":chr(64+fireClass)

                                        }})
                landCoverFile.close()

def markAndFix5OnFires():
        rootFolder = "E:\\ModisImage\\"
        allFires = getAllPathsToImagery(rootFolder,["Fire_Masks"])
        firePaths = filterFiresForPacking(allFires,onFire=5)
        shpFiles = {}
        for i,firePath in enumerate(firePaths):
                print(f"Redownloading fire {i+1} of {len(firePaths)}: ", end="", flush=True)

                fireId = firePath.split("\\")[-2]
                country = firePath.split("\\")[-5]
                month = firePath.split("\\")[-3]
                year = firePath.split("\\")[-4]
                outputPath = rootFolder + "Fire_Masks_OnFire5\\" +country+"\\"+ year + "\\" + month+"\\"+ fireId+"\\"

                if os.path.exists(outputPath):
                        if len(glob.glob(outputPath+"*_fire_*.npy")) == 6:
                                print("Already Exists! Skipped!")
                                continue 

                fireTransform = json.load(open(glob.glob(firePath + "*.json")[0]))
                transform = Affine(fireTransform["a"],fireTransform["b"],fireTransform["c"],fireTransform["d"],fireTransform["e"],fireTransform["f"])

                boundingBox = Polygon([(0,0),(0,512),(512,512),(512,0)])
                boundingBox = affine_transform(boundingBox,transform.to_shapely())
                boundingBox = BBox(boundingBox,CRS.WGS84)

                if country not in shpFiles:
                        shpFiles[country] = loadFiresFromSHP("E:\\Polygons_GlobFire_CALC\\GlobFire_"+country+"_CALC.shp")
                
                fire = list(filter(lambda x: str(x.id)==fireId, shpFiles[country]))
                if fire == []:
                        print(f"Fire {fireId} could not be found in the {country} CALC file.Skipped!")
                        continue
                fire = fire[0]
                timestamps = getFireTimestampsSHub(fire.endDate, fire.startDate,boundingBox ,30)
                downloadImageSet(timestamps,1,5,1,1,boundingBox,outputPath, fireId)
                print("Done!")
        generateMasks()

def check_fires_outside_range():
        all_paths = getAllPathsToImagery("E:\\ModisImage\\",["Fire_Masks"])

        fire_in_the_past = 0
        fire_in_the_future = 0
        for path in all_paths:
                postFirePaths = glob.glob(path+"post_fire_*.npy")
                preFiresPaths = glob.glob(path+"pre_fire_*.npy")
                if any("2017" in s for s in preFiresPaths):
                        fire_in_the_past +=1
                        print(f"Fire {path} has a date in 2017")
                if any("2021" in s for s in postFirePaths):
                        fire_in_the_future +=1
                        print(f"Fire {path} has a date in 2021")

        print (f"A total of {fire_in_the_past} have fires in 2017")
        print (f"A total of {fire_in_the_future} have fires in 2021")

def generate_confusion_matrix():
        fire_dict = {}
        with fiona.open("E:\\EFFIS_Validation\\joint_EFFIS_THESIS.shp") as merged_shp:
                for merged_fire in merged_shp:
                        fire_dict[merged_fire["properties"]["id_2"]] = merged_fire["properties"]["id"]

        all_thesis_fires = glob.glob("E:\\EFFIS_Validation\\Thesis_Selected_Fires\\**\\*_final_mask.png")
        total_confusion_matrix = numpy.nan
        accuracy =0
        precision = 0
        recall = 0
        f1_score_results = 0
        counter = 0

        merged_effis = None
        merged_thesis = None

        for thesis_fire in all_thesis_fires:
                path_split = thesis_fire.split("\\")
                thesis_id = int(path_split[-2])
                if thesis_id not in fire_dict: continue
                effis_path = f"E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR\\Good\\{fire_dict[thesis_id]}\\{fire_dict[thesis_id]}_mask.png"
                if not os.path.exists(effis_path): continue
                binary_thesis = plt.imread(thesis_fire)[:,:,0].flatten()
                binary_effis = plt.imread(effis_path)[:,:,0].flatten()
                
                if merged_effis is None:
                        merged_effis = binary_effis
                else:
                        merged_effis = numpy.concatenate((merged_effis,binary_effis))

                if merged_thesis is None:
                        merged_thesis = binary_thesis
                else:
                        merged_thesis = numpy.concatenate((merged_thesis,binary_thesis))

                if type(total_confusion_matrix) is not numpy.ndarray:
                        total_confusion_matrix = confusion_matrix(binary_effis,binary_thesis)
                else:
                        total_confusion_matrix += confusion_matrix(binary_effis,binary_thesis)
                accuracy += accuracy_score(binary_effis,binary_thesis)
                precision += precision_score(binary_effis,binary_thesis)
                recall += recall_score(binary_effis,binary_thesis)
                f1_score_results += f1_score(binary_effis,binary_thesis)
                counter +=1
                if counter == 50: break
        print(f"images used made: {counter}")
        print("-------------------------- using summed up results ----------------------")
        print(f"confusion matrix total: {total_confusion_matrix}")
        print(f"accuracy total / average: {accuracy}/{accuracy/counter}")
        print(f"precision total / average: {precision}/{precision/counter}")
        print(f"recall total / average: {recall}/{recall/counter}")
        print(f"f1_score total / average: {f1_score_results}/{f1_score_results/counter}")

        print("-------------------------- using merged imagery ----------------------")
        print(f"confusion matrix total: {confusion_matrix(merged_effis,merged_thesis)}")
        print(f"accuracy: {accuracy_score(merged_effis,merged_thesis)}")
        print(f"precision: {precision_score(merged_effis,merged_thesis)}")
        print(f"recall:{recall_score(merged_effis,merged_thesis)}")
        print(f"f1_score:{f1_score(merged_effis,merged_thesis)} ")

def get_maximum_available_dates(paths, cloud_coverage_max):
        before_time_delta = relativedelta(months=-6)
        after_time_delta = relativedelta(weeks=3)
        
        total_before_timestamps = 0
        total_during_timestamps = 0
        total_after_timestamps = 0

        fire_per_country= {}
        file = open(f"E:\\max_date_check_cl_{cloud_coverage_max}.csv", "w")
        csv_file = csv.writer(file)
        csv_file.writerow(["fire_id","before_max_count", "during_max_count","after_max_count"])
        for curr_fire_path in paths:
                fire_id = curr_fire_path.split("\\")[-2]
                country = curr_fire_path.split("\\")[-5]
                if country not in fire_per_country:
                        fire_per_country[country] = loadFiresFromSHP(getRootFolder()+"Polygons_Thesis_CALCBMI\\Version_2_Biomes\\Thesis_" + country + "_CALCBMIB.shp")
                fire = list(filter(lambda x: str(x.id)==fire_id, fire_per_country[country]))
                if fire == []: continue
                fire = fire[0]
                start_date = datetime.strptime(fire.startDate, "%Y-%m-%d")
                end_date = datetime.strptime(fire.endDate, "%Y-%m-%d")

                fire_transform = json.load(open(glob.glob(curr_fire_path + "*.json")[0]))
                transform = Affine(fire_transform["a"],fire_transform["b"],fire_transform["c"],fire_transform["d"],fire_transform["e"],fire_transform["f"])

                bounding_box = Polygon([(0,0),(0,512),(512,512),(512,0)])
                bounding_box = affine_transform(bounding_box,transform.to_shapely())
                bounding_box = BBox(bounding_box,CRS.WGS84)
                bounding_box = [bounding_box.min_x, bounding_box.min_y, bounding_box.max_x, bounding_box.max_y]
                
                before_stamps = searchAllDates(bounding_box,start_date+before_time_delta,start_date,cloud_coverage_max)
                during_stamps = searchAllDates(bounding_box,start_date,end_date,cloud_coverage_max)
                after_stamps = searchAllDates(bounding_box,end_date,start_date+after_time_delta,cloud_coverage_max)

                before_count = len(before_stamps) if before_stamps is not None else 0
                during_count = len(during_stamps) if during_stamps is not None else 0
                after_count = len(after_stamps) if after_stamps is not None else 0
                csv_file.writerow([fire_id, str(before_count),str(during_count),str(after_count)])

                total_after_timestamps +=after_count
                total_before_timestamps += before_count
                total_during_timestamps += during_count
        
        file.close()
        print(f"For selected fires on average we have {total_before_timestamps/len(paths)} before timestamps")
        print(f"For selected fires on average we have {total_during_timestamps/len(paths)} during timestamps")
        print(f"For selected fires on average we have {total_after_timestamps/len(paths)} after timestamps")

def print_max_min_for_type(root_folder, keyword, channel_first = True):
        min_type = None
        max_type = None
        for file in glob.glob(root_folder+"\\**\\*" + keyword+"*.npy",recursive=True):
                narray = numpy.load(file)

                if channel_first:
                        c = narray.shape[0]
                else:
                        c = narray.shape[-1]
                if min_type == None:
                        min_type = [None]*c
                if max_type == None:
                        max_type = [None]*c
                
                for i in range(c):
                        curr_min = numpy.min(narray[i,:,:]) if channel_first else numpy.min(narray[:,:,i])
                        curr_max = numpy.max(narray[i,:,:]) if channel_first else numpy.max(narray[:,:,i])
                        if min_type[i] is None or min_type[i]>curr_min:
                                min_type[i] = curr_min
                        if max_type[i] is None or max_type[i]<curr_max:
                                max_type[i] = curr_max
        
        print(f"Min Values for {keyword} are {min_type}")
        print(f"Max Values for {keyword} are {max_type}")


#Step 1 split globfire files into country files
#processShapeFiles() 

#Step 2 filter and add Land Cover n=> 51%, Area, agriculture CREATES _CALC file
#filterAndUpdateShapeFiles() 

#Step 3 json file created to select fires with most available imagery
#generateTimeStamps() 

#Step 4 download S2 Imagery
#download(363)  

#Step 5
#generateMasks() 

#Step 6
# improveFirePolygons( 
#         "E:\\Polygons_GlobFire_CALC\\",
#         "E:\\ModisImage\\Fire_Masks\\",
#         "final_mask",
#         "E:\\Polygons_Thesis_Results\\Version_4\\","GlobFire_","_CALC", "Thesis_", "_CALCBMI")

# for shpFile in glob.glob("E:\\Polygons_Thesis_Results\\Version_4\\*.shp"):
#         print("")
#         country = shpFile.split("_")[-2]
#         print(f"Doing Biome update for {country}.")
#         fires = loadFiresFromSHP(shpFile)
#         updated_fires = updateFireInfos(fires,True)
#         storeFiresToSHP(updated_fires,"E:\\Polygons_Thesis_Results\\Version_4_Biomes\\",country,"Thesis_","_CALCBMIB")

# Step 7 prep out fwi
all_paths = getAllPathsToImagery("E:\\ModisImage\\",["Fire_Masks"] )

#Step 8 - Package fires into .npz files for training

#checkForStranglers("E:\\ModisImage\\")

# generate_raster_data(all_paths,use_latlong=True)

print("")

#Dataset Creator
print("")
filtered_fires = filterFiresForPacking(all_paths, fireSize = 6 ) #temporalCohesion = True
print("")
if len(filtered_fires) > 559:
        filtered_fires = random.sample(filtered_fires,648)
print(f"We have {len(filtered_fires)} fires")

generateDataSet(filtered_fires, "E:\\Dataset_nomcoherent_size_6_static\\",0.7,True,True,True,True,True,True,True,True)

# biome_dict = {"Boreal Forests" : 6, "Mediterranean Forests" : 4, "Temperate Forest": 16, 
#                 "Temperate Grasslands & Savannas": 26, "Tropical & Subtropic Savanna":467, 
#                 "Tropical Forest":129}

# all_filtered = []
# for b in biome_dict:
#         curr_filtered = filterFiresForPacking(all_paths, biome = b)
#         if len(curr_filtered) > biome_dict[b]:
#                 curr_filtered = random.sample(curr_filtered,biome_dict[b])
#         elif len(curr_filtered) < biome_dict[b]:
#                 print (f"NOT ENOUGH FIRES FOR {b}. WE WANT {biome_dict[b]} WE HAVE AT MOST {len(curr_filtered)}")
#                 exit()
#         all_filtered += curr_filtered

# generateDataSet(all_filtered, "E:\\Dataset_percent_total_nonbalanced_static\\",0.7,True,True,True,True,True,True,True,True)

##Dataset Creator Random Fires
#randomFires = random.sample(getAllPathsToImagery("H:\\ModisImage\\",["Fire_Masks"],countries),1000)


#bounding box for fire

#Add FWI to File

#Update EFFIS Files for EFFIS_Validation
# rootFolder = ("E:\\EFFIS_Validation\\EFFIS_Country_Shp\\")
# rootOutput = ("E:\\EFFIS_Validation\\EFFIS_Country_CALC\\")
# processEFFISFires(rootFolder, rootOutput)

#markAndFix5OnFires()
#generateMasks()


#recomupteMasks()

#create masks from shapefiles
# effis_fires = fiona.open("E:\\EFFIS_Validation\\joint_EFFIS_THESIS.shp")
# imagery_root = "E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR\\"
# output_root = "E:\\EFFIS_Validation\\EFFIS_Poly_to_Mask\\"
# for effis_poly in effis_fires:
#         fire_id = str(effis_poly["properties"]["id"])
#         geometry = shape(effis_poly["geometry"])
#         fire_image_base = imagery_root + fire_id + "\\"
#         if not os.path.exists(fire_image_base):
#                 continue
#         if not os.path.exists(output_root):
#                 os.makedirs(output_root)

#         fire_transform = json.load(open(glob.glob(fire_image_base + "*.json")[0]))
#         transform = Affine(fire_transform["a"],fire_transform["b"],fire_transform["c"],fire_transform["d"],fire_transform["e"],fire_transform["f"])
#         mask = rasterize([geometry],out_shape=(512,512),transform=transform)
#         plt.imsave(output_root+"\\" + fire_id+ "_mask.png",mask,cmap="binary_r")

# root_path = "E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR\\Good\\"
# all_images = os.listdir(root_path)
# shp_file = fiona.open("E:\\EFFIS_Validation\\EFFIS_Selected_Fires_EFFIS_DNBR\\Good\\effis_good.shp",
#                 "w","ESRI Shapefile", 
#                 {"geometry":"Polygon","properties":{"id":"int"}}, 
#                 crs= "EPSG:4326")

# for fire_id in all_images:
#         binary_image = plt.imread(root_path+fire_id+"\\"+fire_id+"_mask.png")[:,:,0]

#         fire_transform = json.load(open(glob.glob(root_path+fire_id+"\\" + "*.json")[0]))
#         transform = Affine(fire_transform["a"],fire_transform["b"],fire_transform["c"],fire_transform["d"],fire_transform["e"],fire_transform["f"])
#         polygon = ops.unary_union(maskToPolygons(binary_image,binary_image==1,transform))
#         shp_file.write({"geometry":mapping(polygon),"properties":{"id":int(fire_id)}})
# shp_file.close()
#generate_confusion_matrix()

# all_shp = glob.glob("E:\\\Polygons_Thesis_Results\\Version_4_Biomes\\*.shp")
# output = "E:\\\Polygons_Thesis_Results\\Version_4_Biomes_Filtered\\"
# for shp in all_shp:
#         base = os.path.basename(shp)
#         country = base.split("_")[-2]
#         old_fires = loadFiresFromSHP(shp)
#         new_fires = []
#         for fire in old_fires:
#                 if fire.getFireClass() < 5: continue
#                 if fire.biome =="Others": continue
#                 new_fires.append(fire)

#         print(f"For {country} we had {len(old_fires)} now we have {len(new_fires)}")
#         storeFiresToSHP(new_fires,output,country,"Thesis_","_CALCBMIB")

# fires_per_country_per_stage = {}
# name_schemes = ["GlobFire_*_CA.shp", "GlobFire_*_CALC.shp","Thesis_*_CALCBMI.shp","Thesis_*_CALCBMIB.shp"]
# folders = ["E:\\Polygons_GlobFire_CA\\", "E:\\Polygons_GlobFire_CALC\\", 
#                 "E:\\\Polygons_Thesis_Results\\Version_4\\", "E:\\\Polygons_Thesis_Results\\Version_4_Biomes_Filtered\\"]

# for i in range(len(folders)):
#         all_countries = glob.glob(folders[i]+name_schemes[i])
#         for country in all_countries:
#                 cFlag = country.split("_")[-2]
#                 shp = fiona.open(country)
#                 if not cFlag in fires_per_country_per_stage:
#                         fires_per_country_per_stage[cFlag] = [0]*len(folders)
                
#                 fires_per_country_per_stage[cFlag][i] = len(shp)
#                 shp.close()

# f = open("E:\\fire_progression_v3.csv", "w")
# csv_file = csv.writer(f)
# csv_file.writerow(["Country","CA Count", "CALC Count","CALCBMI Count", "CALCBMIB Count"])
# for info in fires_per_country_per_stage:
#         csv_file.writerow([info]+fires_per_country_per_stage[info])
# f.close()

#fires per biome per year statistic
# biome_path = "E:\\Polygons_Biomes\\Dinerstein_et_al_2017_Padilla_et_al_2014_Biomes\\Dinerstein_et_al_2017_Padilla_et_al_2014_Biomes_Fixed.shp"
# biomes = {}
# biome_names = []
# with fiona.open(biome_path) as shp_biomes:
#         for b in shp_biomes: 
#                 if b["properties"]["PADILLA"] not in biomes:
#                         biomes[b["properties"]["PADILLA"]] = [shape(b["geometry"])]
#                 else:
#                         biomes[b["properties"]["PADILLA"]].append(shape(b["geometry"]))
#                 if b["properties"]["PADILLA"] not in biome_names:
#                         biome_names.append(b["properties"]["PADILLA"])

# all_modis_files = glob.glob("E:\\MODIS_BA_GLOBAL2018_2020\\*.shp")

# modis_years = numpy.unique([os.path.splitext(os.path.basename(x))[0].split("_")[-1] for x in all_modis_files])

# all_fires_per_biome_per_year = {}
# for biome_name in biome_names:
#         all_fires_per_biome_per_year[biome_name] = {}
#         for modis_year in modis_years:
#                 all_fires_per_biome_per_year[biome_name][modis_year] = 0

# print(all_fires_per_biome_per_year)

# for i,modis_file in enumerate(all_modis_files):
#         print(f"processing modis file {i+1} of {len(all_modis_files)}")
#         with fiona.open(modis_file) as shp_modis:
#                 year = os.path.splitext(os.path.basename(modis_file))[0].split("_")[-1]
#                 for j,fire in enumerate(shp_modis):
#                         print(f"processing fire {j+1} of {len(shp_modis)}",end="\r")
#                         if fire["properties"]["Type"] != "FinalArea":continue

#                         geometry = shape(fire["geometry"])
#                         if not isinstance(geometry, list):
#                                 geometry = [geometry]

#                         s = ops.unary_union(geometry)
#                         wgs84 = pyproj.CRS("EPSG:4326")
#                         destination=pyproj.CRS("EPSG:8857")
#                         transform = pyproj.Transformer.from_crs(wgs84,destination, always_xy=True).transform
#                         polygon_area = ops.transform(transform,s)
#                         endArea = polygon_area.area*0.000247105

#                         if endArea < 300: continue

#                         currMax = 0
#                         currVal = ""
#                         for biome in biomes:
#                                 for poly in biomes[biome]:
#                                         intersectionArea = s.intersection(poly).area
#                                         if intersectionArea>currMax:
#                                                 currMax = intersectionArea
#                                                 currVal = biome
#                         if currVal=="":
#                                 print(f"Fire {fire['properties']['Id']} is weird, since it does not intersect with ANY BIOME")
#                                 continue
#                         all_fires_per_biome_per_year[currVal][year] += 1

# print(all_fires_per_biome_per_year)

# f = open("E:\\fire_per_biome_per_year.csv", "w")
# csv_file = csv.writer(f)
# csv_file.writerow(["Biome Type"] + modis_year)
# for biome in all_fires_per_biome_per_year:
#         csv_file.writerow([biome]+list(all_fires_per_biome_per_year[biome].values()))
# f.close()

