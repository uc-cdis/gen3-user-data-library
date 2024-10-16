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


## Tests

-  test authorize request for all endpoints 
-  test that we don't get ids from other creators when we request a list
- test validate_user_list_item
-  test that the time updated gets changed when list updates
- finish unfinished tests in tests_lists (and maybe by id?)
- test that the Models ensure the extra/invalid fields don't work
- test create and update list with empty, should be 200
- teste append with empty, should be 400
- fix `test_max_limits` so that i can test config without affecting other tests
  right now I have to set the config at the end, seems wrong
  - NOTE: use monkeypatch?
- tests should probably rearranged, specifically middleware
- test max items is not bypassed

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


## Abstractions
-  abstract design for MAX_LISTS/ITEMS
    - max lists should be checked on ANY create, so abstract it from endpoint/db 
    - max items should be checked on ANY create/update, so abstract it from endpoint nuance
    - where should we check config? e.g. where should abstraction be

- think about middleware more, the design is not good
  - specifically, we use regex to figure which endpoint the client is trying to hit
  - is there a better way? 
https://github.com/fastapi/fastapi/issues/486
https://fastapi.tiangolo.com/how-to/custom-request-and-route/

- look up better way to do error handling in fastapi 
   -> referring to make_db req or 500
    - specifically, is there a way to abstract all the exceptions we throw so they're not 
    in the way of all our code?
- change any create or update to throw if no items provided
- if use passes invalid data, throw instead of creating default empty list
- abstract validation step on all endpoints (e.g. MAX ITEM/MAX LISTS)


## Minor Problems
-  fix the base class not having a router in BaseTestRouter
```NOTES: 
https://docs.python.org/3/library/abc.html
alex: label as abstract base class, should provide a way to define that router is required
 abstractbaseclass lib
 find way to define abstract property
 @property
 def router(self):
     raise NotImplemented()
```

## Remaining Work

- Add the auth endpoint hit for specific lists. The endpoint that ensure user has access to
  the specific lists.