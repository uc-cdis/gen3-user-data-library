import json


async def create_basic_list(arborist, get_token_claims, client, user_list, headers, user_id="1"):
    arborist.auth_request.return_value = True
    get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
    response = await client.put("/lists", headers=headers, json={"lists": [user_list]})
    assert response.status_code == 201
    return response


def get_id_from_response(resp):
    return list(json.loads(resp.content.decode('utf-8')).get("lists", {}).items())[0][0]
