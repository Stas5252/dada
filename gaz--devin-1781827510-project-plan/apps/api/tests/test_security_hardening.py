import pytest
import uuid
import ipaddress
import socket
from unittest.mock import patch, MagicMock

from app.schemas import Agent, Tenant
from app.parsers import parse_url

def test_token_masking():
    agent = Agent(
        tenant_id=uuid.uuid4(),
        name="Test",
        prompt="Test",
        telegram_bot_token="secret_token_123"
    )
    
    # When serialized, it should be masked
    serialized = agent.model_dump()
    assert serialized["telegram_bot_token"] == "***"
    
    tenant = Tenant(
        name="Test Tenant",
        settings={
            "vk_group_token": "secret_vk_token",
            "other_setting": "visible"
        }
    )
    serialized_tenant = tenant.model_dump()
    assert serialized_tenant["settings"]["vk_group_token"] == "***"
    assert serialized_tenant["settings"]["other_setting"] == "visible"

def test_ssrf_protection_private_ip():
    with pytest.raises(ValueError, match="Access to private IP addresses is forbidden"):
        parse_url("http://127.0.0.1/admin")
        
    with pytest.raises(ValueError, match="Access to private IP addresses is forbidden"):
        parse_url("http://169.254.169.254/latest/meta-data/")

@patch("socket.gethostbyname")
def test_ssrf_protection_redirect(mock_gethostbyname):
    def mock_dns(host):
        if host == "127.0.0.1":
            return "127.0.0.1"
        return "8.8.8.8"
    mock_gethostbyname.side_effect = mock_dns
    
    # We need to simulate a redirect to a private IP
    from bs4 import BeautifulSoup
    import httpx
    
    mock_client = MagicMock()
    mock_response_1 = MagicMock()
    mock_response_1.is_redirect = True
    mock_response_1.next_request.url = "http://127.0.0.1/admin"
    
    mock_client.get.return_value = mock_response_1
    
    with patch("app.parsers.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        
        # When redirect happens, validate_url will be called on the next_request.url
        # which will resolve to 127.0.0.1 and raise ValueError
        with pytest.raises(Exception, match="Access to private IP addresses is forbidden"):
            parse_url("http://safe-site.com")
            
def test_rls_session_scope_postgres():
    from app.sqlalchemy_store import SqlAlchemyStore
    from app.settings import Settings
    from app.context import current_tenant_id
    
    settings = Settings(database_url="postgresql://user:pass@localhost/db")
    mock_session_factory = MagicMock()
    mock_session = MagicMock()
    mock_session_factory.return_value = mock_session
    mock_session.bind.dialect.name = "postgresql"
    
    store = SqlAlchemyStore(session_factory=mock_session_factory, settings=settings)
    
    # Set context
    tenant_id = str(uuid.uuid4())
    token = current_tenant_id.set(tenant_id)
    
    try:
        with store._session_scope() as session:
            # Verify SET LOCAL was called
            # sqlalchemy text() object is not easily comparable by ==, so we check the string
            calls = mock_session.execute.call_args_list
            assert len(calls) > 0
            # The first argument of the first call is the text() object
            stmt = calls[0][0][0]
            assert "SET LOCAL app.current_tenant_id" in str(stmt)
            assert calls[0][0][1] == {"tenant_id": tenant_id}
    finally:
        current_tenant_id.reset(token)
