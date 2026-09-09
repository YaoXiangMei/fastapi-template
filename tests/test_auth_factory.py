"""认证依赖工厂测试。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
import pytest

from app.core.auth_factory import create_auth_dependency
from app.core.exceptions import UnauthorizedException


def _make_dependency(model=None, token_url="/api/v1/test/login"):
    """辅助：创建 dependency 并 patch select，避免 SQLAlchemy 报错。"""
    if model is None:
        model = MagicMock()
    _, dependency = create_auth_dependency(model, token_url)
    return dependency


class TestCreateAuthDependency:
    """测试 create_auth_dependency 工厂函数。"""

    def test_returns_tuple_of_scheme_and_dependency(self):
        """工厂应返回 (scheme, dependency) 元组。"""
        mock_model = MagicMock()
        scheme, dependency = create_auth_dependency(mock_model, "/api/v1/test/login")

        assert scheme is not None
        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_raises_on_invalid_token(self):
        """无效 token 应抛出 UnauthorizedException。"""
        dependency = _make_dependency()
        mock_db = AsyncMock()

        with patch(
            "app.core.auth_factory.decode_token",
            side_effect=jwt.PyJWTError("Invalid"),
        ):
            with pytest.raises(UnauthorizedException, match="Invalid or expired token"):
                await dependency(token="invalid_token", db=mock_db)

    @pytest.mark.asyncio
    async def test_dependency_raises_on_wrong_token_type(self):
        """非 access 类型 token 应抛出 UnauthorizedException。"""
        dependency = _make_dependency()
        mock_db = AsyncMock()

        with patch(
            "app.core.auth_factory.decode_token",
            return_value={"type": "refresh", "sub": str(uuid4())},
        ):
            with pytest.raises(UnauthorizedException, match="Invalid token type"):
                await dependency(token="refresh_token", db=mock_db)

    @pytest.mark.asyncio
    async def test_dependency_raises_on_user_not_found(self):
        """用户不存在应抛出 UnauthorizedException。"""
        dependency = _make_dependency()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.auth_factory.select", return_value=MagicMock()):
            with patch(
                "app.core.auth_factory.decode_token",
                return_value={"type": "access", "sub": str(uuid4())},
            ):
                with pytest.raises(UnauthorizedException, match="User not found"):
                    await dependency(token="valid_token", db=mock_db)

    @pytest.mark.asyncio
    async def test_dependency_raises_on_disabled_account(self):
        """禁用账号应抛出 UnauthorizedException。"""
        dependency = _make_dependency()
        mock_user = MagicMock()
        mock_user.is_active = False

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.auth_factory.select", return_value=MagicMock()):
            with patch(
                "app.core.auth_factory.decode_token",
                return_value={"type": "access", "sub": str(uuid4())},
            ):
                with pytest.raises(UnauthorizedException, match="Account is disabled"):
                    await dependency(token="valid_token", db=mock_db)

    @pytest.mark.asyncio
    async def test_dependency_raises_on_unverified_account(self):
        """有 is_verified 属性且为 False 的用户应抛出 UnauthorizedException。"""
        dependency = _make_dependency()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.is_verified = False

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.auth_factory.select", return_value=MagicMock()):
            with patch(
                "app.core.auth_factory.decode_token",
                return_value={"type": "access", "sub": str(uuid4())},
            ):
                with pytest.raises(UnauthorizedException, match="Account not verified"):
                    await dependency(token="valid_token", db=mock_db)

    @pytest.mark.asyncio
    async def test_dependency_returns_user_on_success(self):
        """有效 token 和用户应返回用户对象。"""
        dependency = _make_dependency()
        mock_user = MagicMock()
        mock_user.is_active = True
        # 模拟无 is_verified 属性的模型
        del mock_user.is_verified

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.auth_factory.select", return_value=MagicMock()):
            with patch(
                "app.core.auth_factory.decode_token",
                return_value={"type": "access", "sub": str(uuid4())},
            ):
                result = await dependency(token="valid_token", db=mock_db)
                assert result == mock_user
