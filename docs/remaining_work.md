# Remaining Work

List out any remaining work to do here that is NOT a future consideration.
E.G. should be done before release. 

- (hold) TODO dynamically create user policy, ROUGH UNTESTED VERSION: need to verify
  - at line if not config.debug_skip_auth

-  todo: test authorize request for all endpoints 

- TODO: Unsure if this is safe we might need to actually error here?
  - in upsert -> except ArboristError as e: logging.error(e)  

-  todo (addressed): remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}} 

   - NOTES: lib for arborist requests. when a user makes a req, ensure an auth check goes to authz for
  the records they're trying to modify.
  create will always work if they haven't hit limit.
  for modify, get authz from the record.
  make a request for record to arborist with sub id and id, check if they have write access.
  need to check if they have read access.
  filtering db based on the user in the first place, but may one day share with others.
  make sure requests is done efficently.

-  (hold) todo: abstract design for this. ANY create in db should check this, so it should be deep, yes?
MAX_LISTS AND MAX_LIST_ITEMS ^^

-  (hold) TODO?: meant to track overall number of user lists over time, can increase/decrease as they get created/deleted
for TOTAL_USER_LIST_GAUGE

- think about middleware more, the design is not good

-  todo (addressed): move these comments into confluence doc

    claim is a terminology
    token has a bunch of info
    info i "claim" is true
    jwt, sever validates info was not modified and allows you to do what you want to do
    pub/priv key encryption
    fence has both keys, signs token, provides to user
    only fence has priv
    on server side, decode content and ensure it has not been modified
    validating token has not been modified using fence
    if true, returns token contents (encoded json base 64)
    code is defined by oauth
    sub field is required by oauth (sub = subject)
    only use case is to get unique sub id
   
-  todo: test that we don't get ids from other creators when we request a list

-  todo (addressed): fix the base class not having a router in BaseTestRouter

NOTES: 
https://docs.python.org/3/library/abc.html
alex: label as abstract base class, should provide a way to define that router is required
 abstractbaseclass lib
 find way to define abstract property
 @property
 def router(self):
     raise NotImplemented()

-  todo (myself): look up better way to do error handling in fastapi
referring to make_db req or 500

- test validate_user_list_item

-  todo (addressed?): what if they don't have any items? 
    - append: 200 or 400? -> 400
    -  update: 200
    -  create: 200
    - create user list instance

-  todo: double check that we only stop user from adding more than max lists
-  todo (addressed): if no lists when we get should we return 404? yes

- make note in docs: 
  -         # todo (addressed): how to test non-existent user?
          # if they have token they exist, if they don't they're auth
-  todo: test that the time updated gets changed when list updates
- change update to throw if no items provided
-  todo: if user provides fake props
   - error out if they put invalid props in items
   - error out if body has additional fields, gave us more data than we wanted
- make a not in docs that we don't need to worry about a user trying to update
  the wrong list because that's handled in the auth portion
- if use passes invalid data, throw instead of creating default empty list