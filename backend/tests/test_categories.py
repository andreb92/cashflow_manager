def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    from tests.test_onboarding import WIZARD_PAYLOAD
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_list_categories_includes_defaults(client):
    _setup(client)
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    assert any(c["type"] == "Housing" for c in r.json())

def test_create_custom_category(client):
    _setup(client)
    r = client.post("/api/v1/categories", json={"type": "Health", "sub_type": "Gym"})
    assert r.status_code == 200 and r.json()["type"] == "Health"

def test_rename_category_reflects_everywhere(client):
    _setup(client)
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Housing")
    client.put(f"/api/v1/categories/{cat_id}", json={"type": "Home & Living"})
    types = {c["type"] for c in client.get("/api/v1/categories").json()}
    assert "Home & Living" in types

def test_deactivate_category(client):
    _setup(client)
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Leisure")
    client.put(f"/api/v1/categories/{cat_id}", json={"is_active": False})
    cat = next(c for c in client.get("/api/v1/categories").json() if c["id"] == cat_id)
    assert cat["is_active"] is False

def test_delete_unreferenced_category(client):
    _setup(client)
    cat_id = client.post("/api/v1/categories", json={"type": "Temp", "sub_type": "X"}).json()["id"]
    assert client.delete(f"/api/v1/categories/{cat_id}").status_code == 200

def test_delete_referenced_category_returns_409(client, db):
    _setup(client)
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User
    user = db.query(User).filter_by(email="alice@example.com").first()
    cat = db.query(Category).filter_by(user_id=user.id, type="Housing").first()
    pm_id = client.get("/api/v1/payment-methods").json()[0]["id"]
    db.add(Transaction(
        user_id=user.id, date="2026-01-15", detail="Rent", amount=800,
        payment_method_id=pm_id, category_id=cat.id,
        transaction_direction="debit", billing_month="2026-01-01",
    ))
    db.commit()
    assert client.delete(f"/api/v1/categories/{cat.id}").status_code == 409


def test_delete_check_scoped_to_current_user(client, db):
    """Category delete must check only the current user's transactions, not all users'."""
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User
    from tests.test_onboarding import WIZARD_PAYLOAD

    # Register and complete onboarding as Bob (another user who will have transactions)
    client.post("/api/v1/auth/register", json={
        "email": "bob_cat@test.com", "password": "Password1!", "name": "Bob"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    bob = db.query(User).filter_by(email="bob_cat@test.com").first()
    bob_cat = db.query(Category).filter_by(user_id=bob.id, type="Housing").first()
    bob_pm_id = client.get("/api/v1/payment-methods").json()[0]["id"]
    # Bob has a transaction referencing his Housing category
    db.add(Transaction(
        user_id=bob.id, date="2026-01-15", detail="Bob Rent", amount=800,
        payment_method_id=bob_pm_id, category_id=bob_cat.id,
        transaction_direction="debit", billing_month="2026-01-01",
    ))
    db.commit()

    # Register and complete onboarding as Alice
    client.post("/api/v1/auth/register", json={
        "email": "alice_cat@test.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    # Alice creates a fresh category with no transactions referencing it
    alice_cat_id = client.post("/api/v1/categories", json={"type": "AliceCat", "sub_type": "Y"}).json()["id"]
    # Alice should be able to delete her own category (Bob's transactions must not block this)
    resp = client.delete(f"/api/v1/categories/{alice_cat_id}")
    assert resp.status_code == 200
