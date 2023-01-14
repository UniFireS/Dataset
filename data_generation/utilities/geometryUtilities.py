from shapely import ops
from rasterio import Affine, features
import fiona
from datetime import datetime,timedelta
import numpy
import random
import pyproj
import shapely
import math

# -------Checks if polygon is within another polygon ie: if GWIS burn locations are within country borders
def shapeContainsOther(containerShape, containedShape):
    return containedShape.within(containerShape)


def getLargestIntersectingCountry(firePolygon, countryPolygons):
    bestCountry=""
    area =0
    if not isinstance(firePolygon, list):
        firePolygon = [firePolygon]
    firePolygon= ops.unary_union(firePolygon)
    for country in countryPolygons:
        intersection = firePolygon.intersection(countryPolygons[country]).area
        if intersection>area:
            area = intersection
            bestCountry = country
    return bestCountry

# -------Returns the area of polygon in meters squared
def getAreaOfPolygon(shape):
    if not isinstance(shape, list):
        shape = [shape]

    s = ops.unary_union(shape)
    wgs84 = pyproj.CRS("EPSG:4326")
    destination=pyproj.CRS("EPSG:8857")
    transform = pyproj.Transformer.from_crs(wgs84,destination, always_xy=True).transform
    polygon_area = ops.transform(transform,s)
    return polygon_area.area


# ------- checks if all shapes are contained in all containers 
def shapesContainOthers(containers, contained):
    counter = 0
    if not isinstance(containers, list):
        containers = [containers]
    if not isinstance(contained, list):
        contained = [contained]
    for containedSingle in contained:
        for container in containers:
            if shapeContainsOther(container, containedSingle):
                counter += 1

    return counter == len(contained)

# ------- gets bounding box from GWIS for Sentinel2 
def getBoundingBox(polygons):
    poly = ops.unary_union(polygons)
    return poly.bounds


# -------  Transforms binary image to set of polygons  (needed for shapefile of fires to be generated)
def maskToPolygons(image, mask, transform = Affine.identity()):
    if numpy.all(image == 0):
        return []
    output = []
    for shape, value in features.shapes(image.astype(numpy.int16), mask=mask, transform=transform):
        output.append(shapely.geometry.shape(shape))
    return output


# --------- Unified BBox
def unified_bbox(bbox, spatialResolution = 512):
    topCornerCode = getUTMCode(bbox[0], bbox[1])
    topEasting, topNorthing = fiona.transform.transform(
        "EPSG:4326", "EPSG:"+topCornerCode, [bbox[0]], [bbox[1]])
    bottomEasting, bottomNorthing = fiona.transform.transform(
        "EPSG:4326", "EPSG:"+topCornerCode, [bbox[2]], [bbox[3]])
    distEasting = abs(topEasting[0] - bottomEasting[0])
    distNorthing = abs(topNorthing[0] - bottomNorthing[0])
    distance = distEasting if distEasting > distNorthing else distNorthing
    div = distance // (spatialResolution * 10)
    div = div + 0.5 if distance % (spatialResolution*10) >= 256 else div
    newTopEasting = (topEasting[0] + bottomEasting[0]
                     )/2 - spatialResolution*5*(div+1)
    newTopNorthing = (topNorthing[0] + bottomNorthing[0]) / \
        2 - spatialResolution*5*(div+1)
    newBottomEasting = newTopEasting + spatialResolution*10*(div+1)
    newBottomNorthing = newTopNorthing + spatialResolution*10*(div+1)

    topLng, topLat = fiona.transform.transform(
        "EPSG:" + topCornerCode, "EPSG:4326", [newTopEasting], [newTopNorthing])
    bottomLng, bottomLat = fiona.transform.transform(
        "EPSG:" + topCornerCode, "EPSG:4326", [newBottomEasting], [newBottomNorthing])

    return [topLng[0], topLat[0], bottomLng[0], bottomLat[0]]

def getUTMCode(lng, lat):
    """Based on lat and lng, return best utm epsg-code"""
    utm_band = str((math.floor((lng + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
        return epsg_code
    epsg_code = '327' + utm_band
    return epsg_code

# ------- Creates time tupples based on start and end date and amount of slots
def createTimeSlots(startDate: datetime, endDate:datetime, slots:int):
    delta =(endDate-startDate)/slots
    startPoints = [(startDate + i * (delta + timedelta(days=+1))).isoformat() for i in
                        range(slots)]
    endPoints = [(startDate + i * delta + (i - 1) * timedelta(days=+1)).isoformat() for i in
                      range(1, slots + 1)]
    
    return [(startPoints[i],endPoints[i]) for i in range(len(startPoints))]




## --- need to include** -  based on lat and lng, return best utm epsg-code
def getUTMCode(lng, lat):
    utm_band = str((math.floor((lng + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
        return epsg_code
    epsg_code = '327' + utm_band
    return epsg_code
