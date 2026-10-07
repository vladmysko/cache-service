def test_create_payload(client):
    response = client.post(
        "/payload",
        json={
            "list_1": ["first string", "second string"],
            "list_2": ["other string", "another string"],
        },
    )

    assert response.status_code == 201
    assert "id" in response.json()


def test_create_and_get_payload(client):
    create_response = client.post(
        "/payload",
        json={
            "list_1": ["first string", "second string"],
            "list_2": ["other string", "another string"],
        },
    )

    payload_id = create_response.json()["id"]

    response = client.get(
        f"/payload/{payload_id}"
    )

    assert response.status_code == 200

    assert response.json() == {
        "output": (
            "FIRST STRING, OTHER STRING, "
            "SECOND STRING, ANOTHER STRING"
        )
    }


def test_repeated_request_returns_same_id(client):
    request = {
        "list_1": ["hello"],
        "list_2": ["world"],
    }

    first = client.post(
        "/payload",
        json=request,
    )

    second = client.post(
        "/payload",
        json=request,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    assert first.json()["id"] == second.json()["id"]


def test_unknown_payload_returns_404(client):
    response = client.get(
        "/payload/does-not-exist"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Payload not found"
    }


def test_mismatched_lists_return_422(client):
    response = client.post(
        "/payload",
        json={
            "list_1": ["a", "b"],
            "list_2": ["c"],
        },
    )

    assert response.status_code == 422

def test_different_inputs_with_same_output_return_same_id(client):
    first = client.post('/payload', json={'list_1': ['hello'], 'list_2': ['world']})
    second = client.post('/payload', json={'list_1': ['HELLO'], 'list_2': ['WORLD']})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert client.get(f"/payload/{second.json()['id']}").json() == {'output': 'HELLO, WORLD'}


def test_empty_payload_can_be_reused(client):
    request = {'list_1': [], 'list_2': []}
    first = client.post('/payload', json=request)
    second = client.post('/payload', json=request)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert client.get(f"/payload/{first.json()['id']}").json() == {'output': ''}
