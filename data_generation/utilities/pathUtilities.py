
from glob import glob
import os


def getRootFolder():
    return 'E:\\'

def getLandCoverFolder():
    return 'E:\\Polygons_LC100\\'

def getFWIFolder():
    return 'E:\\Raster_Fires_Spread\\FWI_TIFF_IVAN\\'

def getERA5Folder():
    return "E:\\Raster_Fires_Spread\\ERA5\\"
def get_erc_folder():
    return "E:\\Raster_Fires_Spread\\TO_ADD_IF_NEEDED\\ERC2017_2021\\"

def get_gmt_file():
    return "E:\\Raster_Slope_Elevation\\GMTED_MEAN\\merged.tiff"

# -------Returns path to where GWIS (MODIS) shapefiles are stored
def getMODISFolder():
    return getRootFolder() + "MODIS_BA_GLOBAL2018_2020\\"

# -------Returns path to shapefile that contains all of the country borders
def getCountryShapeFile():
    return getRootFolder() + "Polygons_Country\\POLYGON_WORLD\\POLYGON_WORLD_4326.shp"

def getJsonFireDateFolder():
    return getRootFolder() + "Json_Fire_Dates\\"

def getBiomesFile():
    return "E:\\Polygons_Biomes\\Biomes_to_Country.shp"

def getAllPathsToImagery(rootFolder, filters = None, countries = None):
    output = []
    if filters == None:
        filters = os.listdir(rootFolder)
    for filter in filters:
        if countries == None:
            countries = os.listdir(rootFolder + filter + "\\")
        for country in countries:
            filePath = rootFolder + filter+"\\"+country+"\\"
            for year in os.listdir(filePath):
                for month in os.listdir(filePath+year):
                    for fireId in os.listdir(filePath+year+"\\"+month):
                        output.append(filePath+year+"\\"+month+"\\"+fireId+"\\")
    
    return output
