import pytest

@pytest.mark.skip(reason="descoped — see ADR-0011")
def test_descoped_with_explicit_reason():
    """
    Assert this test is skipped with a logged "descoped — see ADR-0011" reason,
    not deleted and not silently passing.
    """
    pass
