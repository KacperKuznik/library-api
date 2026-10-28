BOOK = {"serial_number": "004217", "title": "Lalka", "author": "Bolesław Prus"}


def borrow(client, card="123456"):
    return client.put(
        "/books/004217/status", json={"status": "borrowed", "borrower_card_number": card}
    )


def give_back(client):
    return client.put("/books/004217/status", json={"status": "available"})


def test_add_and_list_books(client):
    response = client.post("/books", json=BOOK)
    assert response.status_code == 201
    assert response.json()["status"] == "available"
    assert client.get("/books").json() == [response.json()]


def test_add_duplicate_book(client):
    client.post("/books", json=BOOK)
    assert client.post("/books", json=BOOK).status_code == 409


def test_add_book_with_invalid_serial_number(client):
    response = client.post("/books", json=BOOK | {"serial_number": "123"})
    assert response.status_code == 422


def test_delete_book(client):
    client.post("/books", json=BOOK)
    assert client.delete("/books/004217").status_code == 204
    assert client.get("/books").json() == []


def test_delete_missing_book(client):
    assert client.delete("/books/999999").status_code == 404


def test_borrow_and_return_book(client):
    client.post("/books", json=BOOK)

    borrowed = borrow(client).json()
    assert borrowed["status"] == "borrowed"
    assert borrowed["borrower_card_number"] == "123456"
    assert borrowed["borrowed_at"] is not None

    returned = give_back(client).json()
    assert returned["status"] == "available"
    assert returned["borrower_card_number"] is None
    assert returned["borrowed_at"] is None


def test_borrow_with_invalid_card_number(client):
    client.post("/books", json=BOOK)
    assert borrow(client, card="12ab").status_code == 422


def test_cannot_borrow_twice(client):
    client.post("/books", json=BOOK)
    borrow(client)
    assert borrow(client).status_code == 409


def test_cannot_return_available_book(client):
    client.post("/books", json=BOOK)
    assert give_back(client).status_code == 409


def test_cannot_delete_borrowed_book(client):
    client.post("/books", json=BOOK)
    borrow(client)
    assert client.delete("/books/004217").status_code == 409
