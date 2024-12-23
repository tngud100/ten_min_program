import pytest
from src.dao.remote_pcs_dao import RemoteDao
from src.models.remote_pcs import RemotePcs

@pytest.mark.asyncio
async def test_insert_remote_pc_server_id(test_session):
    # Given
    server_id = "test_server_123"
    
    # When
    await RemoteDao.insert_remote_pc_server_id(test_session, server_id)
    
    # Then
    result = await test_session.get(RemotePcs, 1)
    assert result is not None
    assert result.server_id == server_id
    assert result.service == "deanak"
    assert result.state == "idle"

@pytest.mark.asyncio
async def test_delete_remote_pc_by_server_id(test_session):
    # Given
    server_id = "test_server_456"
    await RemoteDao.insert_remote_pc_server_id(test_session, server_id)
    
    # When
    await RemoteDao.delete_remote_pc_by_server_id(test_session, server_id)
    
    # Then
    result = await test_session.get(RemotePcs, 1)
    assert result is None
