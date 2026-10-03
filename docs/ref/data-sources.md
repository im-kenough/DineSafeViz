# Data Sources

Both datasets can be downloaded from https://open.toronto.ca/dataset/dinesafe/.

There are two datasets:
1. historical data: from 2001 to 2023-12-29 (.zip, static)
2. recent data: from 2023-11-10 to today (.csv, appended about once per business day)

The two datasets overlap from 2023-11-10 to 2023-12-29. `refresh.py` keeps the
recent rows for that window and drops the historical ones.

Around June 2026, Toronto Public Health (TPH) changed their schema

## Recent Dataset

The recent dataset stores inspection results from 2023-11-10 to today.

On the portal it's a CKAN DataStore resource (`datastore_active: true`): the
CSV is an export of a database table, also available from
`/datastore/dump/<resource id>`. TPH appends a new batch of rows to that table
about once per business day. Existing rows aren't rewritten. Each batch:

- gets the next block of `_id` values, so `_id` order is batch order, not
  inspection date order
- is sorted by establishment name within the batch
- mostly holds the latest inspections, but can also backfill older inspections
  dated as far back as 2023-11

`refresh.py` downloads the whole file on every run and replaces all rows on or
after the file's earliest `inspectionDate`.

It uses this new schema (post 06-2026):

### Data Dictionary

| Column           | Description                                                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| _id              | Unique row identifier for Open Data database                                                                                |
| unique_id        | Unique id for this record connected to source data                                                                          |
| estId            | Establishment ID - this will contain either a legacy id or a new one, depending on the system this data currently lives in. |
| oldEstId         | Legacy establishment ID                                                                                                     |
| estName          | Establishment Name                                                                                                          |
| address          | Address of Establishment                                                                                                    |
| inspectionStatus | Status of the inspection (ex: Pass)                                                                                         |
| phone            | Establishment phone number                                                                                                  |
| inspectionDate   | Date of inspection                                                                                                          |
| observation      | Observation made during inspection                                                                                          |
| typeDesc         | Details of infraction (Open Data portal erroneously has this Category of infraction)                                        |
| deficiencyDesc   | Category of infraction (Open Data portal erroneously has this Details of infraction)                                        |
| severity         | Severity of infraction                                                                                                      |
| OutcomeDate      | Date of outcome of prosecution, if there was one                                                                            |
| OutcomeDesc      | Description of outcome, if there was one - this can be 'pending' if an outcome is being processed                           |
| amountFined      | Dollar amount of fine given                                                                                                 |
| latitude         |                                                                                                                             |
| longitude        |                                                                                                                             |

### Sample Recent data

sample recent data downloaded 2026-10-02

```
_id,unique_id,estId,oldEstId,estName,address,inspectionStatus,phone,inspectionDate,observation,typeDesc,deficiencyDesc,severity,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude
119594,e8d758441838fb943d31cd3811875f96,001Vo000013QngNIAS,10724559,Westside Montessori School,57 Sylvan Ave None M6H 1G4,Pass,6475325321,2026-09-30,No infractions were observed under the Food Premises Regulation during an inspection.,None,None,None,,None,,43.65430076,-79.43242108
119595,8b624d97cf09a135fd9ddff60d6d7b5e,001Vo000013QoNoIAK,10827348,ZHANGTANTAN MALATANG,17A Finch Ave W Unit-A M2N 7K4,Pass,4378808500,2026-10-01,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FAIL TO ENSURE FACILITY SURFACE CLEANED AS NECESSARY - SEC. 22,06. MAINTENANCE / SANITATION OF SANITARY FACILITIES,M - Minor,,None,,43.77920189,-79.41711402
119596,589d62840924c415e4046abadc02522a,001Vo000013QoNoIAK,10827348,ZHANGTANTAN MALATANG,17A Finch Ave W Unit-A M2N 7K4,Pass,4378808500,2026-10-01,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FOOD PREMISE NOT MAINTAINED WITH CLEAN WALLS IN FOOD-HANDLING ROOM - SEC. 7(1)(G),05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT,M - Minor,,None,,43.77920189,-79.41711402
119597,ff558f89e27833503056ac6f57e118ed,001Vo000013Qpz1IAC,10841580,ZUBO ASIAN FUSION,2400 Finch Ave W Unit-1 M9M 2C8,Pass,6476152845,2026-10-01,No infractions were observed under the Food Premises Regulation during an inspection.,None,None,None,,None,,43.75148026,-79.54867627

```

## Historical data

Historic data stores inspection results from 2001 to 2023-12-29 and still uses the legacy (pre 06-2026) schema.

On the portal it's a static file resource (`datastore_active: false`), a ZIP
with one CSV per year (`dinesafe_hist_2001.csv` to `dinesafe_hist_2023.csv`).
It isn't updated.

### Data Dictionary

Rec #
Establishment ID
Inspection ID
Establishment Name
Establishment Type
Establishment Address
Latitude
Longitude
Establishment Status: Pass/Conditional Pass/Closed
Min. Inspections Per Year
Infraction Details
Inspection Date
Severity: C - Crucial, S - Significant, M - Minor, NA - Not Applicable
Action
Outcome
Amount Fined

### Sample historic data

Sample historic data - 2017
```
"Rec #","Establishment ID","Inspection ID","Establishment Name","Establishment Type","Establishment Address","Latitude","Longitude","Establishment Status","Min. Inspections Per Year","Infraction Details","Inspection Date","Severity","Action","Outcome","Amount Fined"
"1","9008018","103913052","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","","2017-02-14","","","",""
"2","9008018","104078913","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","FAIL TO PROVIDE THERMOMETER IN STORAGE COMPARTMENT O. REG  562/90 SEC. 21","2017-10-24","S - Significant","Corrected During Inspection","",""
"3","10500438","104102644","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-12-05","","","",""
"4","10500438","103895923","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-01-20","","","",""
```