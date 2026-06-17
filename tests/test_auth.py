import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.database as app_database
from app.main import app as flask_app
from app.database import Base, User

sync_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=sync_test_engine, expire_on_commit=False)

@pytest.fixture(autouse=True)
def setup_sync_db():
    app_database.SessionLocal.configure(bind=sync_test_engine)
    Base.metadata.create_all(sync_test_engine)
    yield
    Base.metadata.drop_all(sync_test_engine)
    app_database.SessionLocal.configure(bind=app_database.engine)

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    with flask_app.test_client() as client:
        yield client

def test_register_success(client):
    payload = {
        "name": "NewUser",
        "password": "Password123",
        "confirm": "Password123"
    }
    response = client.post('/register', data=payload, follow_redirects=True)
    assert response.status_code == 200
    with TestingSessionLocal() as db:
        user = db.execute(select(User).filter(User.user_name == "NewUser")).scalars().first()
        assert user is not None
        assert user.user_name == "NewUser"

def test_register_duplicate_username(client):
    # Create an existing user
    with TestingSessionLocal() as db:
        existing_user = User(user_name="ExistingUser", password="hashedpassword")
        db.add(existing_user)
        db.commit()

    payload = {
        "name": "ExistingUser",
        "password": "Password123",
        "confirm": "Password123"
    }
    response = client.post('/register', data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Username already exists" in response.data

def test_register_password_mismatch(client):
    payload = {
        "name": "NewUser2",
        "password": "Password123",
        "confirm": "Password321"
    }
    response = client.post('/register', data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

def test_register_missing_fields(client):
    payload = {
        "name": "",
        "password": "Password123",
        "confirm": "Password123"
    }
    response = client.post('/register', data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"All fields are required" in response.data

def test_login_success(client):
    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash("SecretPassword")
    with TestingSessionLocal() as db:
        user = User(user_name="LoginUser", password=hashed)
        db.add(user)
        db.commit()

    payload = {
        "name": "LoginUser",
        "password": "SecretPassword"
    }
    response = client.post('/login', data=payload, follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('username') == "LoginUser"

def test_login_invalid_password(client):
    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash("SecretPassword")
    with TestingSessionLocal() as db:
        user = User(user_name="LoginUser", password=hashed)
        db.add(user)
        db.commit()

    payload = {
        "name": "LoginUser",
        "password": "WrongPassword"
    }
    response = client.post('/login', data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

def test_logout(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 123
        sess['username'] = "ActiveUser"

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'username' not in sess
