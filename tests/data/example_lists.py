VALID_LIST_A = {
    "name": "My Saved List 1",
    "items": {
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        },
        "CF_1": {
            "name": "Cohort Filter 1",
            "type": "Gen3GraphQL",
            "schema_version": "c246d0f",
            "data": {
                "query": "query ($filter: JSON) { _aggregation { subject (filter: $filter) "
                "{ file_count { histogram { sum } } } } }",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"annotated_sex": ["male"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                            {"IN": {"data_format": ["CRAM"]}},
                        ]
                    }
                },
            },
        },
    },
}

VALID_LIST_B = {
    "name": "õ(*&!@#)(*$%)() 2",
    "items": {
        "CF_1": {
            "name": "Some cohort I made with special characters: !@&*(#)%$(*&.?:<>õ",
            "type": "Gen3GraphQL",
            "schema_version": "aacc222",
            "data": {
                "query": "query ($filter: JSON,) {\n"
                "    subject (accessibility: accessible, offset: 0, first: 20, , filter: $filter,) {\n"
                "      \n    project_id\n    \n\n    data_format\n    \n\n    race\n    \n\n"
                "    annotated_sex\n    \n\n    ethnicity\n    \n\n    hdl\n    \n\n    ldl\n    \n    }\n"
                "    _aggregation {\n      subject (filter: $filter, accessibility: accessible) {\n"
                "        _totalCount\n      }\n    }\n  }",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"project_id": ["tutorial-synthetic_data_set_1"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                        ]
                    }
                },
            },
        },
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        },
        "drs://dg.TEST:3418077e-0779-4715-8195-7b60565172f5": {
            "dataset_guid": "phs000002.v2.p2.c2",
            "type": "GA4GH_DRS",
        },
        "drs://dg.4503:edbb0398-fcff-4c92-b908-9e650e0a6eb5": {
            "dataset_guid": "phs000002.v2.p2.c1",
            "type": "GA4GH_DRS",
        },
    },
}

VALID_LIST_C = {
    "name": "My Saved List 3",
    "items": {
        "CF_3": {
            "name": "Cohort Filter 3",
            "type": "Gen3GraphQL",
            "schema_version": "c246d0f",
            "data": {
                "query": "query ($filter: JSON) { _aggregation { subject (filter: $filter) "
                "{ file_count { histogram { sum } } } } }",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"annotated_sex": ["male"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                            {"IN": {"data_format": ["CRAM"]}},
                        ]
                    }
                },
            },
        }
    },
}

VALID_LIST_D = {
    "name": "My Saved List D",
    "items": {
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a04": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        }
    },
}


VALID_LIST_E = {
    "name": "My Saved List E",
    "items": {
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a05": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        }
    },
}

INVALID_LIST_A = {
    "name": "My Saved List AP1",
    "foo": "bar",
    "items": {
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a05": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        }
    },
}


VALID_REPLACEMENT_LIST = {
    "name": "example 2",
    "items": {
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        },
        "CF_2": {
            "name": "Cohort Filter 1",
            "type": "Gen3GraphQL",
            "schema_version": "c246d0f",
            "data": {
                "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { 
            histogram { sum } } } } }""",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"annotated_sex": ["male"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                            {"IN": {"data_format": ["CRAM"]}},
                            {"IN": {"race": ['["hispanic"]']}},
                        ]
                    }
                },
            },
        },
    },
}

VALID_PATCH_BODY = {
    "drs://dg.1234:943200c3-271d-4a04-a2b6-040272239a00": {
        "dataset_guid": "phs000001.v1.p1.c1",
        "type": "GA4GH_DRS",
    },
    "CF_2": {
        "name": "Cohort Filter 1",
        "type": "Gen3GraphQL",
        "schema_version": "c246d0f",
        "data": {
            "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { 
                histogram { sum } } } } }""",
            "variables": {
                "filter": {
                    "AND": [
                        {"IN": {"annotated_sex": ["male"]}},
                        {"IN": {"data_type": ["Aligned Reads"]}},
                        {"IN": {"data_format": ["CRAM"]}},
                        {"IN": {"race": ['["hispanic"]']}},
                    ]
                }
            },
        },
    },
}

VALID_MULTI_LIST_BODY = {"lists": [VALID_LIST_A, VALID_LIST_B]}

PATCH_BODY = {
    "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a99": {
        "dataset_guid": "phs000001.v1.p1.c1",
        "type": "GA4GH_DRS",
    },
    "CF_2": {
        "name": "Cohort Filter 1",
        "type": "Gen3GraphQL",
        "schema_version": "c246d0f",
        "data": {
            "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { 
                histogram { sum } } } } }""",
            "variables": {
                "filter": {
                    "AND": [
                        {"IN": {"annotated_sex": ["male"]}},
                        {"IN": {"data_type": ["Aligned Reads"]}},
                        {"IN": {"data_format": ["CRAM"]}},
                        {"IN": {"race": ['["hispanic"]']}},
                    ]
                }
            },
        },
    },
}
