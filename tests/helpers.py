
async def create_basic_list(arborist, get_token_claims, client, user_list, headers):
    arborist.auth_request.return_value = True
    user_id = "79"
    get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
    response = await client.put("/lists", headers=headers, json={"lists": [user_list]})
    assert response.status_code == 201
    return response
