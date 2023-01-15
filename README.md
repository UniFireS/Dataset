
The process to create a global wildfire dataset with high resolution is multifaceted. Each major step in the process creates a shapefile, as an integrated safeguard against unwanted internet crashes. The list of shapefiles can be seen in bold in the below process. 


![Burn_Mask_Creation](https://user-images.githubusercontent.com/122684788/212544605-32651dba-ad53-462d-8265-f6a4fbab6315.png)

The initial focus of this project were on the following countries: Algeria, Angola (split into 2 shapefiles due to size), Argentina, Australia, Brazil, Bulgaria, Cameroon (split into 2 shapefiles due to size), Canada, Chile, China, Colombia, Democratic Republic of The Congo, Ethiopia, France, Greece, Indonesia, Italy, Kazakhstan, Mongolia, Norway, Portugal, Romania, Russian Federation, Spain, Sudan, Sweden, Turkey, Ukraine, United Republic of Tanzania, United States, and Zambia. These countries were selected based on their major biomes, typical size of fire, and amount of fires. 

<b>Initial Filtering</b>

The GlobFire database was used was the original fire perimeters (who leverage's MODIS's MCD64A1 burnt areas). Fires with a start date between 2018-2020 were initially selected. This code then added country location and fire size, and filtered based on the previously mentioned countries and then on fire size, in order to focus on just fires >= 300 acres (size E fire).

The Copernicus Global Land Service: Land Cover 100m (CGLS-LC100) was then used to determine the predominat land cover type for each fire. Since the original focus of this dataset was on forest fires, only those fires with a predominant landcover of >= 51% were included. 



<b>Sentinel Hub MetaData Search</b>
The metadata search submits a request to the Sentinel-Hub that searches for imagery based on timestamps and tile cloud coverage.  The timestamp search determines the amount of available for each fire 120 days before the start of the fire (pre-fire), those available during the fire ("onfire"), and the amount available within 45 days of the end date of the fire (post-fire). Fires are selected if they have at least: five "pre-fire", at least one "onfire" image, and at least one "post-fire" image available (all of which can be updated by the user). All imagery must have a tile cloud cover of <= 30%. Per the code, available fires are written to a json file, which are then downloaded based on the amount of available "onfire" images, with a preference for those fires that have the most available "onfire" images.  

A depiction of an ideal fire can be seen below. 

![Timeline_Preferred](https://user-images.githubusercontent.com/122684788/212545694-fc7b2f71-6c23-48dc-a889-639ef4ab01cf.png)

<b>Secondary Filter</b>
After the metadata search, the Sen2Cor SCL mask is first downloaded for each of the six available satellite images, and is then checked at the scene level for cloud coverage of <10%, and a pixel availability > 30%  for the scene (ie: <30% of the scene is classified per the SCL as "no data").

If either of these criteria are not met, than that fire image is disregarded and the next is downloaded. If there are at least 6 available images per fire, per the SCL filter, than all of the bands for each satellite image are downloaded. If there are not, than the fire is disregarded. 

Clouds that are still within the scene will later be labeled as "SCL Not Burnable" by the code, and those pixels are then removed from the classification. 

If there is sufficient imagery, then the imagery download begins and the \gls{nir} band gets upsampled as it downloads.  


![step1](https://user-images.githubusercontent.com/122684788/212544575-c2bd3842-4d93-4349-981e-575223d60a7b.png)




![FiresByBiome](https://user-images.githubusercontent.com/122684788/212544467-9494f795-203b-4b40-86f5-76a1fbf286e7.png)
