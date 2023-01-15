
<h1>UniFireS</h1>
This dataset was created using GlobFire 500m burnt areas in combination with Sentinel-2 imagery to create 10m burnt area perimeters as part of a Masters Thesis for the Technical University of Munich. The decisions made while creating this dataset were heavily influenced by the EFFIS'S Burnt Areas creation process. This project was supported by the ESA Network of Resources Initiative.

![step1](https://user-images.githubusercontent.com/122684788/212547118-1679f0bb-d04b-4faf-9108-f6b413de46ab.png)

<h3>Dataset Creation</h3>
The process to create a global wildfire dataset with high resolution is multifaceted. Each major step in the process creates a shapefile, as an integrated safeguard against unwanted internet crashes. The list of shapefiles can be seen in bold in the below process. 

![Burn_Mask_Creation](https://user-images.githubusercontent.com/122684788/212544605-32651dba-ad53-462d-8265-f6a4fbab6315.png)

The initial focus of this project were on the following countries: Algeria, Angola (split into 2 shapefiles due to size), Argentina, Australia, Brazil, Bulgaria, Cameroon (split into 2 shapefiles due to size), Canada, Chile, China, Colombia, Democratic Republic of The Congo, Ethiopia, France, Greece, Indonesia, Italy, Kazakhstan, Mongolia, Norway, Portugal, Romania, Russian Federation, Spain, Sudan, Sweden, Turkey, Ukraine, United Republic of Tanzania, United States, and Zambia. These countries were selected based on their major biomes, typical size of fire, and amount of fires. 

<h3>Initial Filtering</h3>
The GlobFire database was used was the original fire perimeters (who leverage's MODIS's MCD64A1 burnt areas). Fires with a start date between 2018-2020 were initially selected. This code then added country location and fire size, and filtered based on the previously mentioned countries and then on fire size, in order to focus on just fires >= 300 acres (size E fire).


<h3>Land Cover Filter</h3>
The Copernicus Global Land Service: Land Cover 100m (CGLS-LC100) was then used to determine the predominat land cover type for each fire. Since the original focus of this dataset was on forest fires, only those fires with a predominant landcover of >= 51% were included. Due to file size, each country was manually clipped from the CGLS-LC100 using QGIS. An example of a "clipped" Brazil can be seen below.

<center><img src="https://user-images.githubusercontent.com/122684788/212546867-4e85f2c6-7472-4da8-8d13-b9cd1a7b6310.png" alt="Brazil Landcover" class="center" width="550" height="550"></center>


<h3>Sentinel Hub MetaData Search</h3>
The metadata search submits a request to the Sentinel-Hub that searches for imagery based on timestamps and tile cloud coverage.  The timestamp search determines the amount of available for each fire 120 days before the start of the fire (pre-fire), those available during the fire ("onfire"), and the amount available within 45 days of the end date of the fire (post-fire). Fires are selected if they have at least: five "pre-fire", at least one "onfire" image, and at least one "post-fire" image available (all of which can be updated by the user). All imagery must have a tile cloud cover of <= 30%. Per the code, available fires are written to a json file, which are then downloaded based on the amount of available "onfire" images, with a preference for those fires that have the most available "onfire" images.  

A depiction of an ideal fire can be seen below. 


<img src="https://user-images.githubusercontent.com/122684788/212545694-fc7b2f71-6c23-48dc-a889-639ef4ab01cf.png" alt="Preferred Timeline" class="center">



<h3>Secondary Filter</h3>
After the metadata search, the Sen2Cor SCL mask is first downloaded for each of the six available satellite images, and is then checked at the scene level for cloud coverage of <10%, and a pixel availability > 30%  for the scene (ie: <30% of the scene is classified per the SCL as "no data").

If either of these criteria are not met, than that fire image is disregarded and the next is downloaded. If there are at least 6 available images per fire, per the SCL filter, than all of the bands for each satellite image are downloaded (the NIR band gets upsampled to 10m as it downloads). If there are not, than the fire is disregarded. 

<h3>Scene Classification</h3>
For the available imagery, the SCL mask is used once again to remove "Not Burnable" areas. This code removes the: No Data,  Saturated/Defective, Cloud Shadow, Clouds Medium Probability, Clouds High Probability, and Snow/Ice categories; in order to avoid additional confusion when creating the burn masks. While the SCL also classifies Water and Bare Soils, after visual inspection, the NDWI was used to remove water pixels and the Bare Soil pixels were kept.

<h3>Burn Severity Indices</h3>
The NBR, dNBR, RdNBR and RBR were calcuated for all fires. A threshold was implemented to ensure only pixels with values of "Moderate-Low Severity" were included. A morphological methodology was then impletmented after the burn indice was applied, to remove stray pixels and provide a more clear burnt area perimeter. A visual inspection using False Color imagery was then completed for each fire, and the index that matched the true boundary of the burnt area was selected. Any fire that did have an index that represented the burnt area to a "very good" level, was removed. 

![BurnSeverityDiagram](https://user-images.githubusercontent.com/122684788/212548044-e9e03448-9517-4a26-b154-bc1c0bc79022.png)

<h3>Comparison of GlobFire, EFFIS, and UniFireS</h3>
A visual review of the fire ID23749235 shapefile from GlobFire, EFFIS, and UniFireS can be seen below. 
![comparisoneffisglobuni](https://user-images.githubusercontent.com/122684788/212548373-66cb4356-05a3-411d-9f88-c7b97da18621.png)

<h3>Finalized Dataset</h3>
This dataset contains 4,081 fires from six major forest biomes and covers 13 different land cover types. The biome distribution of this dataset: 

![Screenshot (3)](https://user-images.githubusercontent.com/122684788/212548770-e9911aef-d919-462f-aa30-2050e649a0e0.png)

Covering a total of 26,902,328.4ha of burnt area, the landcover distribution of this dataset: 


![image](https://user-images.githubusercontent.com/122684788/212548605-5a912cb1-3928-4cc2-bd3f-d35cd9e5851a.png)

The burn indice distribution of this dataset:

![image](https://user-images.githubusercontent.com/122684788/212548619-ce4359de-3f73-48bd-b4f5-a6f763571af0.png)


An overall understanding of the location of each fire and its burn index can be seen below:

![FiresByBiome](https://user-images.githubusercontent.com/122684788/212544467-9494f795-203b-4b40-86f5-76a1fbf286e7.png)
