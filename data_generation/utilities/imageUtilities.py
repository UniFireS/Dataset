from glob import glob
import math
import matplotlib.pyplot as plt
import matplotlib
import numpy
from scipy import ndimage
import cv2 as cv
from matplotlib import cm
import rasterio
import os

from data_generation.preprocessing import dynamicScaleArray

# ------- Remaps RBR to integer values for image saving
def remapRBR(rbr):
    remapped = numpy.zeros((rbr.shape[0], rbr.shape[1]))
    for x in range(remapped.shape[0]):
        for y in range(remapped.shape[1]):
            if math.isnan(rbr[x, y]):
                remapped[x, y] = numpy.nan
            elif rbr[x, y] <= 0.1:
                remapped[x, y] = 1
            elif rbr[x, y] <= 0.27:
                remapped[x, y] = 2
            elif rbr[x, y] <= 0.44:
                remapped[x, y] = 3
            elif rbr[x, y] <= 0.66:
                remapped[x, y] = 4
            else:
                remapped[x, y] = 5

    return remapped

# ------- Remaps dNBR to integer values for image saving
def remapDNBR(dnbr):
    remapped = numpy.zeros((dnbr.shape[0], dnbr.shape[1]))
    for x in range(remapped.shape[0]):
        for y in range(remapped.shape[1]):
            if math.isnan(dnbr[x, y]):
                remapped[x, y] = numpy.nan
            elif dnbr[x, y] <= -0.251:
                remapped[x, y] = 1
            elif dnbr[x, y] <= -0.101:
                remapped[x, y] = 2
            elif dnbr[x, y] <= 0.099:
                remapped[x, y] = 3
            elif dnbr[x, y] <= 0.269:
                remapped[x, y] = 4
            elif dnbr[x, y] <= 0.439:
                remapped[x, y] = 5
            elif dnbr[x, y] <= 0.659:
                remapped[x, y] = 6
            elif dnbr[x, y] <= 1.3:
                remapped[x, y] = 7
            else :
                remapped[x,y] = 8
    return remapped

def remapDNBREFFIS(dnbr):
    remapped = numpy.zeros((dnbr.shape[0], dnbr.shape[1]))
    for x in range(remapped.shape[0]):
        for y in range(remapped.shape[1]):
            if math.isnan(dnbr[x, y]):
                remapped[x, y] = numpy.nan
            elif dnbr[x, y] <= 0.09:
                remapped[x, y] = 1
            elif dnbr[x, y] <= 0.255:
                remapped[x, y] = 2
            elif dnbr[x, y] <= 0.41:
                remapped[x, y] = 3
            elif dnbr[x, y] <= 0.66:
                remapped[x, y] = 4
            else: 
                remapped[x,y] = 5

    return remapped

# ------- Remaps BAIS2 to integer values for image saving
# def remapBAIS2(dbais2):
#     remapped = numpy.zeros((dbais2.shape[0], dbais2.shape[1]))
#     for x in range(remapped.shape[0]):
#         for y in range(remapped.shape[1]):
#             if math.isnan(dbais2[x, y]):
#                 remapped[x, y] = numpy.nan
#             elif dbais2[x, y] <= 1.04: #low
#                 remapped[x, y] = 1
#             elif dbais2[x, y] <= 1.18: #moderate
#                 remapped[x, y] = 2
#             elif dbais2[x, y] <= 1.23: #high
#                 remapped[x, y] = 3
#     return remapped
# -------  Save SCL as colored image based on SCL classification

# No Data (0) = black
# Saturated / Defective (1) = red
# Dark Area Pixels (2) = chocolate
# Cloud Shadows (3) = brown
# Vegetation (4) = lime
# Bare Soils (5) = yellow
# Water (6) = blue
# Clouds low probability / Unclassified (7) = aqua 
# clouds medium probability (8) = darkgrey
# Clouds high probability (9) light grey
# Cirrus (10) = deepskyblue
# Snow / Ice (11) = magenta
#  colors: https://matplotlib.org/3.1.1/gallery/color/named_colors.html#sphx-glr-gallery-color-named-colors-py

def storeSCL(image, filePath):
    cmap = matplotlib.colors.ListedColormap(
        ["black", "red", "chocolate", "brown", "lime", "yellow", "blue","aqua","darkgrey","lightgrey","deepskyblue", "magenta"]) 
    plt.imsave(filePath, image, cmap=cmap, vmin=0, vmax=11)


#0 (no clouds), 1 (clouds), and 255 (no data) ***NO LONGER DOWNLOADED**
# def storeCLM(image, filePath):
#     cmap = matplotlib.colors.ListedColormap(
#         ["white", "blue", "black"]) 
#     plt.imsave(filePath, image, cmap=cmap, vmin=0, vmax=255)




# -------  Saves RBR as colored image based on thresholds
def storeRBR(rbr, filePath):
    cmap = matplotlib.colors.ListedColormap(
        ["gray", "gray", "orange", "red", "purple"])  # ["blue", "teal", "green", "yellow", "orange", "red", "purple"]

    plt.imsave(filePath, remapRBR(rbr), cmap=cmap, vmin=1, vmax=5)

# -------  Saves dnbr as colored image based on thresholds
def storeDNBR(dnbr, filePath):
    cmap = matplotlib.colors.ListedColormap(
        # ["blue", "teal", "green", "yellow", "orange", "red", "purple"]
        ["gray", "gray", "gray", "gray", "orange", "red", "purple", "white"]
    )
    
    plt.imsave(filePath, remapDNBR(dnbr), cmap=cmap, vmin= 1, vmax=8)


# # -------  Saves BAIS2 as colored image based on thresholds
# def storeBAIS2(dbais2, filePath):
#     cmap = matplotlib.colors.ListedColormap(
#         ["gray", "red", "purple"]) 

#     plt.imsave(filePath, remapBAIS2(dbais2), cmap=cmap, vmin=1, vmax=)




# -------  Computes NDWI for water mask
def computeNDWIMask(image):
    rImage, cImage, chImage = image.shape
    ndwiOutput = numpy.zeros((rImage, cImage))

    for x in range(cImage):
        for y in range(rImage):
            if image[y,x,2] ==0 and image[y,x,7] == 0:
                ndwiPixel = 1
            else:
                ndwiPixel = (image[y, x, 2] - image[y, x, 7]) / (image[y, x, 2]+image[y, x, 7])
            ndwiOutput[y, x] = 1 if ndwiPixel >= 0.0 else 0

    return ndwiOutput

# -------  ComputesNDVI mask for (additional) water mask, bare soil,  and man made structures (i.e. buildings and roads) ***NO LONGER IN USE****
# def computeNDVIMask(image):
#     rImage,cImage,chImage = image.shape
#     ndviOutput = numpy.zeros((rImage,cImage))
#     for x in range(cImage):
#         for y in range(rImage):
#             if image[y,x,7] ==0 and image[y,x,3] == 0: 
#                 ndviPixel = 0
#             else: 
#                 ndviPixel = (image[y,x,7] - image[y,x,3]) / (image[y,x,7] + image[y,x,3])
#             ndviOutput[y,x] = 1 if ndviPixel <=0.1 else 0
    
#     return ndviOutput

def computeNDVI(image):
    r,c,ch = image.shape
    ndviOutput = numpy.zeros((r,c))
    for x in range(c):
        for y in range(r):
            if image[y,x,7] ==0 and image[y,x,3] == 0: 
                ndviOutput[y,x] = 0
            else: 
                ndviOutput[y,x] = (image[y,x,7] - image[y,x,3]) / (image[y,x,7] + image[y,x,3])
    
    return ndviOutput

# -------  Utilizies SCL mask for 0 No Data, 1 Saturated Pixels, 3 Cloud Shadow, 8 Clouds Medium Probability, 9 Clouds High Probability,  11 Snow/Ice
# No Data (0) = black


def computeSCLMask(image):
    rImage,cImage = image.shape
    sclOutput = numpy.zeros((rImage,cImage))
    for x in range(cImage):
        for y in range(rImage):
            sclOutput[y,x] = 1 if image[y,x] in [0,1,3,8,9,11] else 0
    
    return sclOutput

def compute_nbr(image):
    rows,columns, channels = image.shape
    nbr = numpy.zeros((1,rows,columns))

    for x in range(columns):
        for y in range(rows):
            if image[y,x,7] == 0 and image[y,x,11] == 0:
                nbr[0,y,x] = 0
            else:
                nbr[0,y,x] = (image[y,x,7] - image[y,x,11]) / (image[y,x,7]+image[y,x,11])
    
    return nbr



# -------  Transforms binary image to set of polygons 
def computeFireMasks(preMask, postMask, preImage, postImage, indices = [7,11]):

    rows, columns, channels = preImage.shape
    nbrPost = numpy.zeros((rows, columns))
    nbrPre = numpy.zeros((rows, columns))
    rbr = numpy.zeros((rows, columns))
    dnbr = numpy.zeros((rows, columns))
    rdnbr = numpy.zeros((rows,columns))
    # bais2Pre = numpy.zeros((rows,columns))
    # bais2Post = numpy.zeros((rows,columns))
    # dbais2 = numpy.zeros((rows,columns))

    for x in range(columns):
        for y in range(rows):

            if preMask[y, x] == 0 and postMask[y, x] == 0:
                nbrPost[y, x] = (postImage[y, x, indices[0]] - postImage[y, x, indices[1]]) / \
                    (postImage[y, x, indices[0]] + postImage[y, x, indices[1]])
                nbrPre[y, x] = (preImage[y, x, indices[0]] - preImage[y, x, indices[1]]) / \
                    (preImage[y, x, indices[0]] + preImage[y, x, indices[1]])
                dnbr[y, x] = nbrPre[y, x] - nbrPost[y, x]
                rbr[y, x] = dnbr[y, x] / (nbrPre[y, x] + 1.001)
                
                # bais2Pre[y,x] = (1-(math.sqrt(preImage[y, x, 5]*preImage[y, x, 6]*(preImage[y, x, 8]/preImage[y, x, 3])))) * ((preImage[y, x, 11]-preImage[y, x, 8])/(math.sqrt(preImage[y, x, 11]+preImage[y, x, 8])+1))
                # bais2Post[y,x] = (1-(math.sqrt(postImage[y, x, 5]*postImage[y, x, 6]*(postImage[y, x, 8]/postImage[y, x, 3])))) * ((postImage[y, x, 11]-postImage[y, x, 8])/(math.sqrt(postImage[y, x, 11]+postImage[y, x, 8])+1))
                
                # if bais2Pre[y,x] == 0 : dbais2[y,x] = 0
                # else: dbais2[y,x] = bais2Pre[y, x] - bais2Post[y, x]             

                if nbrPre[y,x] == 0 : rdnbr[y,x] = 0
                else: rdnbr[y,x] = dnbr[y,x] /math.sqrt(abs(nbrPre[y,x]))




            else:
                rdnbr[y,x] = -50
                rbr[y, x] = -50
                dnbr[y, x] = -50
                # bais2Pre[y, x] = -50  
                # bais2Post[y, x] = -50  
                # dbais2[y, x] = -50
                nbrPre[y, x] = -50
                nbrPost[y, x] = -50

    return [rdnbr, rbr, dnbr]

# -------  Writes binary image to file
def writeBinaryFile(mask, name):
    plt.imsave(name, mask, cmap=cm.binary_r)

# -------  Creates bianry image based on threshold
def createBinaryImage(image, threshold):
    rows, columns = image.shape
    mask = numpy.zeros((rows, columns))
    for x in range(columns):
        for y in range(rows):
            mask[y, x] = True if image[y, x] > threshold else False

    return mask

# -------  Removes noise (smaller pixels) from image with structure = as kernel size
def removeNoise(image, method="closing", iterationSteps=1, structure= (3,3), structType = "square"):
    if structType == "square":
        mask = numpy.ones(structure)
    elif structType == "circle":
        mask = numpy.zeros(structure)
        center = int(structure[0]/2)
        cv.circle(mask,(center,center),int(structure[0]/2),255,-1)
    if method == "closing":
        return ndimage.binary_closing(image,structure=mask,iterations=iterationSteps)
    if method == "dilation":
        return ndimage.binary_dilation(image,structure=mask,iterations=iterationSteps)
    if method == "erosion":
        return ndimage.binary_erosion(image, structure=mask,iterations=iterationSteps)

# -------  Removes noise using contour recognition
def removeSmallContours(image, pixelArea):
    image = image.astype(numpy.uint8)
    contours, hierarchy = cv.findContours(
        image, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)
    toRemoveContours = numpy.ones(image.shape[:2], dtype="uint8")
    for contour in contours:
        if isContourSmall(contour, pixelArea):
            cv.drawContours(toRemoveContours, [contour], -1, 0, -1)
    output = cv.bitwise_and(image, toRemoveContours)
    return output

def fillContours(image, minSize):
    image = image.astype(numpy.uint8)
    contours, hierarchy = cv.findContours(
        image, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)
    newImage = numpy.zeros(image.shape[:2],dtype="uint8")

    filteredContours = []
    for c in contours:
        if cv.contourArea(c)>minSize:
            filteredContours.append(c) 

    cv.drawContours(newImage,filteredContours,-1,255,-1)
    return newImage

# -------  Returns true if total area is smaller than pixel area threshold
def isContourSmall(contour, pixelArea):
    area = cv.contourArea(contour)
    return area < pixelArea


def showImage(image):
    plt.imshow(image)
    plt.show()

def clip_and_scale(image_path, geometry, output_width, output_height):
    if type(geometry) is not list:
        geometry = [geometry]
    with rasterio.open(image_path) as image:
        clip,_ = rasterio.mask.mask(image,geometry,crop=True)
        c,w,h = clip.shape
        clip = numpy.nan_to_num(clip)
        upscaled_clipping = ndimage.zoom(clip, [1,output_width/w,output_height/h])
    return upscaled_clipping

def visualise_numpy(image,output_folder, output_file_name, channel_combos = None):
    if isinstance(image, str):
        image = numpy.load(image)
    elif not isinstance(image, numpy.ndarray):
        return
    
    if len(image.shape) == 2:
        c = 1
    else:
        c = image.shape[0]
    
    if channel_combos is None:
        if c == 1 :
            channel_combos = [[0,0,0]]
        elif c % 3 == 0:
            channel_combos = [[x,x+1,x+2] for x in range(0,c,3)]
        else:
            channel_combos = [[x,x,x] for x in range(c)]
    else:
        new_subband = []
        for subband in channel_combos:
            if len(subband) != 3:
                for i in range(0,len(subband),3):
                    if i+2<len(subband):
                        new_subband.append(subband[i:i+3])
                    else:
                        new_subband.append([subband[i]]*3)
                        if i+1<len(subband):
                            new_subband.append([subband[i+1]]*3)
            else:
                new_subband.append(subband)
        channel_combos = new_subband
    image = ((dynamicScaleArray(image)+1)*127.5).astype(numpy.uint8)
    
    for channel_combo in channel_combos:
        plt.imsave(output_folder + output_file_name + 
        f"_channels{channel_combo}.png", numpy.moveaxis(image[channel_combo,:,:],0,-1))

def create_monthly_mean(root_folder):
    """
    Assume root_folder\<year>\<month>\<day>\<name>.tiff structure
    """
    for year in os.listdir(root_folder):
        for month in os.listdir(root_folder + "\\" + year+"\\"):
            if os.path.isfile(root_folder +  year + "\\" + month): continue
            if os.path.exists(root_folder +  year + "\\" + month+"\\monthly_mean.tiff") : continue

            output_folder = root_folder +  year + "\\" + month + "\\"
            all_day_file_paths = glob(output_folder+"**\\*.tiff")
            all_day_tiffs = []
            for file_path in all_day_file_paths:
                with rasterio.open(file_path) as curr_image:
                    all_day_tiffs.append(curr_image.read())
                    profile = curr_image.profile
            profile_out = profile.copy()
            merged_tiffs = numpy.mean((all_day_tiffs), axis = 0)
            profile_out.update(dtype=merged_tiffs.dtype.name)
            with rasterio.open(output_folder+"monthly_mean.tiff","w",**profile_out) as dst:
                dst.write(merged_tiffs)
