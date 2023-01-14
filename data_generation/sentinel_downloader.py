from oauthlib.oauth2 import BackendApplicationClient
import datetime
from requests_oauthlib import OAuth2Session  # oath for sentinel
from rasterio.io import MemoryFile
from time import sleep
import json
import time
import os
import numpy
import io  # controls writing and reading for files
import tifffile as tiff
import matplotlib.pyplot as plt #saving image




#-----Update here and Authentication 
CLIENT_ID = "CLIENT ID HERE"
CLIENT_SECRET = "CLIENT SECRET HERE"


client = BackendApplicationClient(client_id=CLIENT_ID)
oauth = OAuth2Session(client=client)

token = oauth.fetch_token(token_url='https://services.sentinel-hub.com/oauth/token',
                          client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
token_creation_time = time.time()

def processRequest(type, url, headers, json):
    global token,token_creation_time
    responseCode = 500
    while responseCode != 200:
    # send the request
        if (time.time()-token_creation_time)>token["expires_in"]- 100:
            token = oauth.fetch_token(token_url='https://services.sentinel-hub.com/oauth/token',
                              client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
            token_creation_time = time.time()
    
        response_search = oauth.request(type, url, headers=headers, json=json)

#----- Added this section to define the issue with the server 
        responseCode = response_search.status_code
        if responseCode != 200:
            print("Got error code " + str(responseCode) + " trying again")
        if responseCode == 429:
            print("We sent too many requests. Sleeping for 5 minutes then trying again.")
            sleep(5*60)
        if responseCode == 403:
            print("Got error code " + str(responseCode) + " stopping")
            exit() 
        if responseCode == 400:
            print(response_search.content)
            exit()
    
    return response_search

def searchDate(bbox, startDate, endDate):
    collection_id = "sentinel-2-l2a"
    json_search = {
        'bbox': bbox,
        'datetime': f'{startDate}T00:00:00Z/{endDate}T23:59:59Z',
        'collections': [collection_id],
        'limit': 1
    }

    # set the url and headers
    url_search = 'https://services.sentinel-hub.com/api/v1/catalog/search'
    headers_search = {
        'Content-Type': 'application/json'
    }

    
    response_search = processRequest("POST",url_search,headers_search,json_search)

    results = response_search.json()
    if len(results["features"]) == 0:
        return None
    cloud_coverage = results['features'][0]['properties']['eo:cloud_cover']
    return cloud_coverage

def searchAllDates(bbox, startDate, endDate, cloudCoverage):
    days = (endDate -startDate).days
    endDate = datetime.datetime.strftime(endDate,"%Y-%m-%d")
    startDate = datetime.datetime.strftime(startDate, "%Y-%m-%d")

    collection_id = "sentinel-2-l2a"
    json_search = {
        'bbox': bbox,
        'datetime': f'{startDate}T00:00:00Z/{endDate}T23:59:59Z',
        'collections': [collection_id],
        'limit': 100,
        "query": {
            "eo:cloud_cover": {
                "lt": cloudCoverage
            }
        },
        "distinct":"date"
    }

    # set the url and headers
    url_search = 'https://services.sentinel-hub.com/api/v1/catalog/search'
    headers_search = {
        'Content-Type': 'application/json'
    }

    
    response_search = processRequest("POST",url_search,headers_search,json_search)

    results = response_search.json()
    if len(results["features"]) == 0:
        return None
    return results["features"]



def getOptionalBands(bbox, startDate, endDate):
    collection_id = "sentinel-2-l2a"

    evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["SCL"],
                }],
                output: {
                    bands: 1,
                    sampleType: "UINT8"
                }
            };
        }

        function evaluatePixel(sample) {
                return [sample.SCL];
        }
    """

#------ THIS section was reverted back to the json_request since the MimeType.TIFF DOES NOT HANDLE GeoTIFFs, this function portion allows us to create shapefiles further on

    json_request = {
        'input': {
            'bounds': {
                'bbox': bbox,
                'properties': {
                    'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'
                }
            },
            'data': [
                {
                    'type': 'S2L2A',
                    'dataFilter': {
                        'timeRange': {
                            'from': f'{startDate}T00:00:00Z',
                            'to': f'{endDate}T23:59:59Z'
                        },
                        'mosaickingOrder': 'mostRecent'
                    },
                }
            ]
        },
        'output': {
            'width': 512,
            'height': 512,
            'responses': [
                {
                    'identifier': 'default',
                    'format': {
                        'type': 'image/tiff',
                    }
                }
            ]
        },
        'evalscript': evalscript
    }

    # Set the request url and headers
    url_request = 'https://services.sentinel-hub.com/api/v1/process'
    headers_request = {
        "Authorization": "Bearer %s" % token['access_token']
    }

    response = processRequest("POST",url_request,headers_request,json_request)
    
    bands = tiff.imread(io.BytesIO(response.content))
    return bands

#----- Update below savePath = image_date, id, country plus a Prefix to show which image is pre fires and which is post fires
def requestData(bbox, startDate, endDate, savePath, filePrefix):
    evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B01","B02","B03","B04","B05","B06","B07","B08","B8A","B09","B11","B12"],
                    units: "DN"
                }],
                output: {
                    bands: 12,
                    sampleType: "INT16"
                }
            };
        }

        function evaluatePixel(sample) {
                return [sample.B01,
                        sample.B02,
                        sample.B03,
                        sample.B04,
                        sample.B05,
                        sample.B06,
                        sample.B07,
                        sample.B08,
                        sample.B8A,
                        sample.B09,
                        sample.B11,
                        sample.B12];
        }
    """
#------ THIS section was reverted back to the json_request since the MimeType.TIFF DOES NOT HANDLE GeoTIFFs, this function portion allows us to create shapefiles further on

    json_request = {
        'input': {
            'bounds': {
                'bbox': bbox,
                'properties': {
                    'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'
                }
            },
            'data': [
                {
                    'type': 'S2L2A',
                    'dataFilter': {
                        'timeRange': {
                            'from': f'{startDate}T00:00:00Z',
                            'to': f'{endDate}T23:59:59Z'
                        },
                        #'maxCloudCoverage': 30,
                        'mosaickingOrder': 'leastCC',
                        'other_args' :{'processing': {'upsampling': 'BICUBIC', 'downsampling':'BILINEAR'}} 
                    },
                }
            ]
        },
        'output': {
            'width': 512,
            'height': 512,
            'responses': [
                {
                    'identifier': 'default',
                    'format': {
                        'type': 'image/tiff',
                    }
                }
            ]
        },
        'evalscript': evalscript
    }

    # Set the request url and headers
    url_request = 'https://services.sentinel-hub.com/api/v1/process'
    headers_request = {
        "Authorization": "Bearer %s" % token['access_token']
    }

    response = processRequest("POST",url_request,headers_request,json_request)
# ----- Updated slightly in order extract information from GeoTIFF
    if not os.path.exists(savePath):
        os.makedirs(savePath)

    all_bands_response = tiff.imread(io.BytesIO(response.content))
    geoTiff = MemoryFile(io.BytesIO(response.content)).open()
    transform = geoTiff.transform

    image = numpy.array(all_bands_response)[:,:,[3,2,1]]
    image = image / 10000
    save_image = numpy.clip(image*3.5,0,1)

    numpy.save(savePath+filePrefix+"_"+startDate+".npy",all_bands_response)
    plt.imsave(savePath + filePrefix + "_" + startDate + ".png", save_image)

    jsonTransform = {"a":transform.a,"b":transform.b,"c":transform.c,"d":transform.d,"e":transform.e,"f":transform.f}
    with open(savePath+filePrefix+"_"+startDate+".json","w") as fp:
        json.dump(jsonTransform,fp=fp)

    return (all_bands_response, transform)
