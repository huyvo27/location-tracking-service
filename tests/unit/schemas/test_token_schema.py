from app.schemas.token import Token, TokenData


def test_token_defaults():
    token = Token(access_token="abc123")
    assert token.access_token == "abc123"
    assert token.token_type == "bearer"


def test_token_custom_type():
    token = Token(access_token="xyz789", token_type="custom")
    assert token.token_type == "custom"


def test_token_data_with_sub():
    data = TokenData(sub="user_uuid")
    assert data.sub == "user_uuid"


def test_token_data_without_sub():
    data = TokenData()
    assert data.sub is None
