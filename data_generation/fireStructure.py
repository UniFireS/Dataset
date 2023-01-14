
# ------- Fireclass describing fires for internal use
import datetime
import shapely.ops as ops
import pyproj

class Fire():
    def __init__(self, id: int, startDate: str, endDate: str, areaA = 0, areaHA = 0, country = "") -> None:
        self.startDate = startDate
        self.endDate = endDate
        self.firePolygons = {}
        self.id = id
        self.areaHA = areaA
        self.areaA = areaHA
        self.country = country
        self.landCover = 255
        self.biome = ""
        self.maskType = ""
        self.onFireDates = 0

    def __lt__(self, other):
        return self.endDate <other.endDate

    def addFireDate(self, date: str, polygon):
        if self.startDate > date:
            self.startDate = date
        if self.endDate < date:
            self.endDate = date

        if date not in self.firePolygons:
            self.firePolygons[date] = [polygon]
        else:
            self.firePolygons[date].append(polygon)

    def getFireDuration(self):
        sd = datetime.datetime.strptime(self.startDate, "%Y-%m-%d")
        ed = datetime.datetime.strptime(self.endDate, "%Y-%m-%d")

        return (ed-sd).days
    
    def getLastFirePolygon(self):
        return self.firePolygons[self.endDate]
    
    def getFireClass(self):

        shape = self.firePolygons[self.endDate]
        if not isinstance(shape, list):
            shape = [shape]

        s = ops.unary_union(shape)
        wgs84 = pyproj.CRS("EPSG:4326")
        destination=pyproj.CRS("EPSG:8857")
        transform = pyproj.Transformer.from_crs(wgs84,destination, always_xy=True).transform
        polygon_area = ops.transform(transform,s)
        endArea = polygon_area.area*0.000247105

        if endArea<0.25:
            return 1
        elif endArea<10:
            return 2
        elif endArea<100:
            return 3
        elif endArea<300:
            return 4
        elif endArea<1000:
            return 5
        elif endArea<5000:
            return 6
        else:
            return 7
