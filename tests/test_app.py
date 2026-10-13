from app.models import Application, Vendor


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "VulaTrust" in response.text


def test_home_page_counts(client, db):
    vendor = Vendor(name="Example Files")
    db.add_all(
        [
            vendor,
            Application(name="Assigned", vendor=vendor),
            Application(name="Unassigned one"),
            Application(name="Unassigned two"),
        ]
    )
    db.commit()

    html = client.get("/").text
    assert "<strong>1</strong>Vendors" in html
    assert "<strong>3</strong>Applications" in html
    assert "<strong>2</strong>Unassigned applications" in html
