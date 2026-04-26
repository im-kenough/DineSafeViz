# Overview

The DineSafe dataset looks like this


```markdown
| _id | Establishment ID | Inspection ID | Establishment Name | Establishment Type | Establishment Address | Infraction Details | Inspection Observation | Inspection Date | Severity | Action | Outcome | Outcome Date | Amount Fined | Latitude | Longitude | unique_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 10752656 | None | # HASHTAG INDIA RESTAURANT | Food Take Out | 1871 O'CONNOR DR None M4A 1X1 | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22 | One or more minor infractions were observed under the Food Premises Regulation during an inspection. | 2024-03-06 | M - Minor | Notice to Comply | None |  |  | 43.72199 | -79.30349 | 168f86274045194142c0e7c381ccb75d |
| 2 | 001Vo000013QjzHIAS | None | #DESI | Food Take Out | 65 Front St W Unit-442 M5J 1E6 | FOOD PREMISE NOT MAINTAINED WITH CLEAN WALLS IN FOOD-HANDLING ROOM - SEC. 7(1)(G)   | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-03-04 | M - Minor | Notice to Comply | None |  |  | 43.645275 | -79.380486 | d6b83968d597f037799eb07945d261f1 |
| 3 | 10817087 | None | 000 BLUEPRINT CLUB | Food Take Out | 1 BLUE JAYS WAY None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-11 | None | None | None |  |  | 43.64168 | -79.39012 | 1207a0bbb785902f3df59027ade39708 |
| 4 | 001Vo000013QnH0IAK | None | 000 CLOVER BANNER CLUB KITCHEN | Food Take Out | 1 Blue Jays Way None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-04 | None | None | None |  |  | 43.64168 | -79.39012 | 0800ecf1e1ba903a76ac7badb1d754a3 |
| 5 | 001Vo000013Qhj7IAC | None | 000 MEZZ PRODUCTION KITCHEN (PK) | Commissary | 1 Blue Jays Way None M5V 1J4 | FOOD PREMISE NOT MAINTAINED WITH FOOD HANDLING ROOM IN SANITARY CONDITION - SEC. 7(1)(E)  | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-04-11 | M - Minor | Notice to Comply | None |  |  | 43.64168 | -79.39012 | ee0f219eedadbb3580ace8aaff396397 |
| 6 | 10817088 | None | 000 TD LOUNGE | Food Take Out | 1 BLUE JAYS WAY None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-04 | None | None | None |  |  | 43.64168 | -79.39012 | 699cf64aa42c1ee0e6fe5b767703ce81 |
| 7 | 001Vo000013QnGiIAK | None | 000 THE WAREHOUSE (docks) | Commissary | 1 Blue Jays Way None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-08-09 | None | None | None |  |  | 43.64168 | -79.39012 | e605e36388c6fbe5176dd514ac5e5949 |
| 8 | 001Vo000013QnGcIAK | None | 000F BLUEPRINT CLUB KITCHEN | Banquet Facility | 1 Blue Jays Way None M5V 1J4 | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22 | One or more minor infractions were observed under the Food Premises Regulation during an inspection. | 2025-03-27 | M - Minor | Notice to Comply | None |  |  | 43.64168 | -79.39012 | 8bd58999ca6747cebd449e81a9198ac0 |
```

# Data Dictionary

Column	Description
_id	

Unique row identifier for Open Data database
Establishment ID	Unique identifier for an establishment
Inspection ID	Unique ID for an inspection
Establishment Name	Business name of the establishment
Establishment Type	Establishment type ie restaurant, mobile cart
Establishment Address	Municipal address of the establishment
Infraction Details	Description of the Infraction
Inspection Observation	Details observed associated with the Infraction
Inspection Date	Calendar date the inspection was conducted
Severity	Level of the infraction, i.e. S - Significant, M - Minor, C - Crucial
Action	Enforcement activity based on the infractions noted during a food safety inspection
Outcome	The registered court decision resulting from the issuance of a ticket or summons for outstanding infractions to the Health Protection and Promotion Act
Outcome Date	The date of the court outcome
Amount Fined	Fine determined in the court outcome
Latitude	Latitude of establishment
Longitude	Longitude of establishment
unique_id	Unique composite key