import glob
import os
import numpy as np
import random
import cv2

def generateDataSet(allFolderPaths,outputFolder,split =0.7,colourMapping = True, 
                    use_fwi=False,use_era5=False,use_nbr=False,use_landcover=False, use_erc= False, use_gmt = False, use_latlong = False):
    files_per_fire = 7
    if use_fwi:
        files_per_fire +=6
    if use_era5:
        files_per_fire += 3*6
    if use_nbr:
        files_per_fire +=6
    if use_landcover:
        files_per_fire +=6
    if use_erc:
        files_per_fire +=6
    if use_gmt:
        files_per_fire += 6
    if use_latlong:
        files_per_fire += 6*2

    trainPath = outputFolder + "Dataset\\train\\"
    testPath = outputFolder + "Dataset\\test\\"

    if not os.path.exists(trainPath):
        os.makedirs(trainPath)
    if not os.path.exists(testPath):
        os.makedirs(testPath)

    selectedFires = [] #selectedFires structures 5 prefires and postfire 
    #loop through all the subfolders in the fire folder
    for fireFolder in allFolderPaths:
                    #fetch the pre_fires first
        if(len(glob.glob(fireFolder+"\\pre_fire_*.npy"))!=5):
            print(fireFolder)
            print("prefire")
            continue    
        if(len(glob.glob(fireFolder+"\\post_fire_*.npy"))!=1):
            print(fireFolder)
            print("postfire")
            continue      
        if(len(glob.glob(fireFolder+"\\*_final_mask.png"))!=1):
            print(fireFolder)
            print("fire mask")
            continue
        if(len(glob.glob(fireFolder+ "\\fwi_*"))!=6 and use_fwi):
            print(fireFolder)
            print("fwi")
            continue
        if(len(glob.glob(fireFolder+ "\\humidity_*"))!=6 and use_era5):
            print(fireFolder)
            print("humidity")
            continue
        if(len(glob.glob(fireFolder+ "\\precipitation_*"))!=6 and use_era5):
            print(fireFolder)
            print("percipitation")
            continue
        if(len(glob.glob(fireFolder+ "\\wind_*"))!=6 and use_era5):
            print(fireFolder)
            print("wind")
            continue
        if(len(glob.glob(fireFolder+ "\\nbr_*"))!=6 and use_nbr):
            print(fireFolder)
            print("nbr")
            continue
        if(len(glob.glob(fireFolder+ "\\lc_*"))!=6 and use_landcover):
            print(fireFolder)
            print("lc")
            continue
        if(len(glob.glob(fireFolder+ "\\erc_*"))!=6 and use_erc):
            print(fireFolder)
            print("erc")
            continue
        if(len(glob.glob(fireFolder+ "\\gmt_*"))!=6 and use_gmt):
            print(fireFolder)
            print("gmt")
            continue
        if(len(glob.glob(fireFolder+ "\\latitude_*"))!=6 and use_gmt):
            print(fireFolder)
            print("latitude")
            continue
        if(len(glob.glob(fireFolder+ "\\longitude_*"))!=6 and use_gmt):
            print(fireFolder)
            print("latitude")
            continue  

        selectedFires += glob.glob(fireFolder+"\\pre_fire_*.npy")
        selectedFires += glob.glob(fireFolder+"\\post_fire_*.npy")
        selectedFires += glob.glob(fireFolder+"\\*_final_mask.png") #mask for post_fire dnbr image
        if use_fwi:
            selectedFires += glob.glob(fireFolder+"\\fwi_*")
        if use_era5:
            selectedFires += glob.glob(fireFolder+ "\\humidity_*")
            selectedFires += glob.glob(fireFolder+ "\\precipitation_*")
            selectedFires += glob.glob(fireFolder+ "\\wind_*")
        if use_nbr:
            selectedFires += glob.glob(fireFolder+ "\\nbr_*")
        if use_landcover:
            selectedFires += glob.glob(fireFolder+ "\\lc_*")
        if use_erc:
            selectedFires += glob.glob(fireFolder + "\\erc_*")
        if use_gmt:
            selectedFires += glob.glob(fireFolder + "\\gmt_*")
        if use_latlong:
            selectedFires += glob.glob(fireFolder + "\\latitude_*")
            selectedFires += glob.glob(fireFolder + "\\longitude_*")

    #total datapoints
    numFires = int(len(selectedFires)/files_per_fire)
    #splits
    fireTrain = int(split*numFires)
    fireTest = numFires-fireTrain
    #indices for ease of access
    fireIndices = list(range(numFires))
    random.shuffle(fireIndices)
    #split of indices
    fireTrainIndices = fireIndices[:fireTrain]
    fireTestIndices = fireIndices[fireTrain:]

    create_dataset_component(trainPath,selectedFires,fireTrainIndices,colourMapping,files_per_fire,use_fwi,use_era5,use_nbr,use_landcover,use_erc,use_gmt,use_latlong)
    create_dataset_component(testPath,selectedFires,fireTestIndices,colourMapping,files_per_fire,use_fwi,use_era5,use_nbr,use_landcover,use_erc,use_gmt,use_latlong)

def create_dataset_component(output_path, data_source, indicies, colour_mapping, files_per_fire, use_fwi, use_era5, use_nbr,use_landcover,use_erc,use_gmt, use_latlong): 
    channel_count = 12
    if use_fwi:
        channel_count += 1
    if use_era5:
        channel_count += 3
    if use_nbr:
        channel_count += 1
    if use_landcover:
        channel_count += 1
    if use_erc:
        channel_count += 1
    if use_gmt:
        channel_count += 1
    if use_latlong:
        channel_count +=2
    for i in range(len(indicies)):
        print(f"Creating Train Data Point {i+1} of {len(indicies)}",end="\r")
        index = indicies[i]
        if colour_mapping:
            timeSeries = np.zeros((5,512,512,channel_count),dtype="uint8")
        else:
            timeSeries = np.zeros((5,512,512,channel_count),dtype=np.float32)
        for j in range(5):
            tsImage = process_file_for_fire(data_source,files_per_fire*index,j,use_fwi,use_era5,use_nbr,use_landcover,use_erc,use_gmt, use_latlong, colour_mapping)
            timeSeries[j] = tsImage
        fImage = process_file_for_fire(data_source,files_per_fire*index, 5, use_fwi,use_era5,use_nbr,use_landcover,use_erc,use_gmt,use_latlong, colour_mapping)
        mask = cv2.imread(data_source[files_per_fire*index + 6])
        mask_identifier = flagToInt(os.path.basename(data_source[files_per_fire*index + 6]).split("_")[0][1:])
        savePath = output_path + str(i) +  ".npz"
        np.savez_compressed(savePath, time_series = timeSeries,future_image=fImage,fire_mask=mask,label=mask_identifier)

def process_file_for_fire(data_source, fire_root, file_offset, use_fwi, use_era5, use_nbr,use_landcover, use_erc, use_gmt,use_latlong,colour_mapping):
    fwi_offset = 7
    era5_offset = 7
    nbr_offset = 7
    landcover_offset = 7
    erc_offset = 7
    gmt_offset = 7
    latlong_offset = 7
    if use_fwi:
        era5_offset += 6
        nbr_offset += 6
        landcover_offset += 6
        erc_offset += 6
        gmt_offset += 6
        latlong_offset += 6
    if use_era5:
        nbr_offset += 6*3
        landcover_offset += 6*3
        erc_offset += 6*3
        gmt_offset += 6*3
        latlong_offset += 6*3
    if use_nbr:
        landcover_offset += 6
        erc_offset += 6
        gmt_offset += 6
        latlong_offset += 6
    if use_landcover:
        erc_offset += 6
        gmt_offset += 6
        latlong_offset +=6
    if use_erc:
        gmt_offset += 6
        latlong_offset += 6
    if use_gmt:
        latlong_offset += 6

    tsImage = np.load(data_source[fire_root+file_offset])
    if use_fwi:
        fwiImage =np.moveaxis(np.load(data_source[fire_root + file_offset + fwi_offset]),0,-1)
    if use_era5:
        hImage = np.moveaxis(np.load(data_source[fire_root + 3*file_offset + era5_offset]),0,-1)
        pImage = np.moveaxis(np.load(data_source[fire_root + 3*file_offset + era5_offset+6]),0,-1)
        wImage = np.moveaxis(np.load(data_source[fire_root + 3*file_offset + era5_offset+2*6]),0,-1)
    if use_nbr:
        nbrImage = np.moveaxis(np.load(data_source[fire_root + file_offset + nbr_offset]),0,-1)
    if use_landcover:
        lcImage = np.moveaxis(np.load(data_source[fire_root + file_offset + landcover_offset]),0,-1)
    if use_erc:
        ercImage = np.moveaxis(np.load(data_source[fire_root + file_offset + erc_offset]),0,-1)
    if use_gmt:
        gmtImage = np.moveaxis(np.load(data_source[fire_root + file_offset + gmt_offset]),0,-1)
    if use_latlong:
        latImage = np.moveaxis(np.load(data_source[fire_root + file_offset + latlong_offset]),0,-1)
        longImage = np.moveaxis(np.load(data_source[fire_root + file_offset + latlong_offset+6]),0,-1)

    if colour_mapping:
        if use_fwi:
            fwiImage = (static_scale_array(fwiImage,0,175)*255).astype("uint8")
        if use_era5:
            hImage = (static_scale_array(hImage,0,270)*255).astype("uint8")
            pImage = (static_scale_array(pImage,0,1)*255).astype("uint8")
            wImage = (static_scale_array(wImage,0,10)*255).astype("uint8")
        if use_nbr:
            nbrImage = (static_scale_array(nbrImage,-1,1)*255).astype("uint8")
        if use_landcover:
            lcImage = (static_scale_array(lcImage,0,255)*255).astype("uint8")
        if use_erc:
            ercImage = (static_scale_array(ercImage,-2,75)*255).astype("uint8")
        if use_gmt:
            gmtImage = (static_scale_array(gmtImage,-25,4800)*255).astype("uint8")
        if use_latlong:
            latImage = (static_scale_array(latImage,-90,90)*255).astype("uint8")
            longImage = (static_scale_array(longImage,-180,180)*255).astype("uint8")

        tsImage = (static_scale_array(tsImage,0,10000,3.5 )*255).astype("uint8")
    else:
        if use_fwi:
            fwiImage = dynamicScaleArray(fwiImage)
        if use_era5:
            hImage =dynamicScaleArray(hImage)
            pImage = dynamicScaleArray(pImage)
            wImage = dynamicScaleArray(wImage)
        if use_nbr:
            nbrImage = dynamicScaleArray(nbrImage)
        if use_landcover:
            lcImage = dynamicScaleArray(lcImage)
        if use_erc:
            ercImage = dynamicScaleArray(ercImage)
        if use_gmt:
            gmtImage = dynamicScaleArray(gmtImage)
        if use_latlong:
            latImage = dynamicScaleArray(latImage)
            longImage = dynamicScaleArray(longImage)            
        tsImage  = dynamicScaleArray(tsImage)
    
    if np.isnan(np.sum(tsImage)):
        print("Image is NAN: " + data_source[fire_root+file_offset])

    if use_fwi:
        if np.isnan(np.sum(fwiImage)):
            print("FWI IS NAN: " + data_source[fire_root + file_offset + fwi_offset])
        tsImage = np.append(tsImage,fwiImage,axis=2)
    if use_era5:
        if np.isnan(np.sum(hImage)):
            print("Humidity IS NAN: " + data_source[fire_root + file_offset + era5_offset])
        tsImage = np.append(tsImage,hImage,axis=2)
        if np.isnan(np.sum(pImage)):
            print("Precipitation IS NAN: " + data_source[fire_root + file_offset + era5_offset + 6 ])        
        tsImage = np.append(tsImage,pImage,axis=2)
        if np.isnan(np.sum(wImage)):
            print("Wind IS NAN: " + data_source[fire_root + file_offset + era5_offset+2*6])        
        tsImage = np.append(tsImage,wImage,axis=2)
    if use_nbr:
        if np.isnan(np.sum(nbrImage)):
            print("NBR IS NAN: "  + data_source[fire_root + file_offset + nbr_offset])
        tsImage = np.append(tsImage, nbrImage, axis=2)
    if use_landcover:
        if np.isnan(np.sum(lcImage)):
            print("LandCover IS NAN: " + data_source[fire_root + file_offset + era5_offset])
        tsImage = np.append(tsImage, lcImage, axis=2)
    if use_erc:
        if np.isnan(np.sum(ercImage)):
            print("ERC IS NAN: " + data_source[fire_root + file_offset + erc_offset])
        tsImage = np.append(tsImage,ercImage,axis=2)
    if use_gmt:
        if np.isnan(np.sum(gmtImage)):
            print("ERC IS NAN: " + data_source[fire_root + file_offset + gmt_offset])
        tsImage = np.append(tsImage,gmtImage,axis=2)
    if use_gmt:
        if np.isnan(np.sum(latImage)):
            print("LAT IS NAN: " + data_source[fire_root + file_offset + latlong_offset])
        tsImage = np.append(tsImage,latImage,axis=2)
        if np.isnan(np.sum(longImage)):
            print("LONG IS NAN: " + data_source[fire_root + file_offset + latlong_offset + 6])
        tsImage = np.append(tsImage,longImage,axis=2)

    
    return tsImage

def flagToInt(flag:str)->int:
    if flag.lower() == "rdnbr":
        return 0
    elif flag.lower() == "rbr":
        return 1
    elif flag.lower() == "dnbr":
        return 2
    return -1


def dynamicScaleArray(array):
    w,h,c = array.shape
    array = array.astype(np.float32)
    output = np.zeros_like(array,np.float32)
    for channel in range(c):
        r = np.max(array[:,:,channel]) - np.min(array[:,:,channel])
        if r == 0:
            output[:,:,channel] = 0
        else:
            output[:,:,channel] = (array[:,:,channel] - np.min(array[:,:,channel]))/r
            output[:,:,channel] = 2 * output[:,:,channel] - 1
    if np.isnan(np.sum(output)):
        print("I FUCKED THE SCALING")
    return output

def static_scale_array(array, min, max, additional_scale = 1):
    array = (array-min)/(max-min)
    return np.clip(array*additional_scale,0,1)