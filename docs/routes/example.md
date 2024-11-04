```
CREATE & UPDATE Body for /lists
------------------------------------

 {
   "lists": [
   {
     "name": "My Saved List 1",
     "items": {
       "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
         "dataset_guid": "phs000001.v1.p1.c1",
             },
       "CF_1": {
        "name": "Cohort Filter 1",
        "type": "Gen3GraphQL",
         "schema_version": "c246d0f",
         "data": { "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter)
         { file_count { histogram { sum } } } } }""", "variables": { "filter": { "AND": [ {"IN":
         {"annotated_sex": ["male"]}}, {"IN": {"data_type": ["Aligned Reads"]}}, {"IN":
         {"data_format": ["CRAM"]}}, {"IN": {"race": ["[\"hispanic\"]"]}} ] } } }
             }
     }
   },
       { ... }
   ]
 }
 ```
