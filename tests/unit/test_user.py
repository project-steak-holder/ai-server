from src.models.user import User


def test_user_creation(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.createdAt is not None
    assert user.updatedAt is not None


def test_user_defaults_nullable_fields(db_session):
    user = User()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.name is None
    assert user.email is None
