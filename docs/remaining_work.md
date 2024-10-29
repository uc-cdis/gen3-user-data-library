# Remaining Work

List out any remaining work to do here that is NOT a future consideration.
E.G. should be done before release. 


## Needs clarification

### Ask Alex (Unaddressed notes)
- dynamically create user policy, ROUGH UNTESTED VERSION: need to verify
  - taken from line `if not config.debug_skip_auth`
- Unsure if this is safe we might need to actually error here?
  - in upsert -> except ArboristError as e: logging.error(e)  
- meant to track overall number of user lists over time, can increase/decrease 
as they get created/deleted -> for `TOTAL_USER_LIST_GAUGE`
- Do we really want to throw if they add extra unused params? fastapi doesn't


## Auth Work
-  remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}} 

   - NOTES: lib for arborist requests. when a user makes a req, ensure an auth check goes to authz for
  the records they're trying to modify.
  create will always work if they haven't hit limit.
  for modify, get authz from the record.
  make a request for record to arborist with sub id and id, check if they have write access.
  need to check if they have read access.
  filtering db based on the user in the first place, but may one day share with others.
  make sure requests is done efficently.


## Minor Issues 
- fix `test_get_token` yellow bits
- 

## Refactoring
- refactor dependencies

## Needs Implemented
