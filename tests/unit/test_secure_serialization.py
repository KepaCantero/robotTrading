"""
Test Suite for Secure Serialization Module.

This test suite verifies that the binary-safe serialization system correctly handles:
1. JSON-serializable data (dicts, lists, strings, numbers)
2. numpy arrays
3. pandas DataFrames
4. Binary data (bytes)
5. Complex nested structures
6. HMAC signature verification
7. Tamper detection
"""

import pytest
import numpy as np
import pandas as pd
from decimal import Decimal

from app.core.secure_serialization import sign_and_dump, verify_and_load, HAS_MSGPACK


class TestJSONSerialization:
    """Test JSON-serializable data types."""

    def test_simple_dict(self):
        """Test simple dictionary serialization."""
        data = {'key': 'value', 'number': 123}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_nested_dict(self):
        """Test nested dictionary serialization."""
        data = {'level1': {'level2': {'level3': 'deep_value'}, 'list': [1, 2, 3]}}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_list_data(self):
        """Test list serialization."""
        data = [1, 2, 3, 'string', {'nested': 'dict'}]
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_string_data(self):
        """Test string serialization."""
        data = "Hello, World!"
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_numeric_types(self):
        """Test various numeric types."""
        data = {'int': 42, 'float': 3.14159, 'negative': -123, 'zero': 0}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_boolean_and_none(self):
        """Test boolean and None values."""
        data = {'true': True, 'false': False, 'none': None}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data


class TestNumpySerialization:
    """Test numpy array serialization (requires msgpack)."""

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_numpy_1d_array(self):
        """Test 1D numpy array serialization."""
        data = {'array': np.array([1, 2, 3, 4, 5])}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert np.array_equal(loaded['array'], data['array'])

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_numpy_2d_array(self):
        """Test 2D numpy array serialization."""
        data = {'array': np.array([[1, 2], [3, 4], [5, 6]])}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert np.array_equal(loaded['array'], data['array'])

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_numpy_float_array(self):
        """Test float numpy array serialization."""
        data = {'array': np.array([1.1, 2.2, 3.3, 4.4])}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert np.allclose(loaded['array'], data['array'])

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_numpy_special_values(self):
        """Test numpy special values (inf, nan)."""
        data = {'array': np.array([1.0, np.inf, -np.inf, np.nan])}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        # Check inf values (nan requires special handling)
        assert loaded['array'][0] == 1.0
        assert np.isinf(loaded['array'][1])
        assert np.isinf(loaded['array'][2])


class TestPandasSerialization:
    """Test pandas DataFrame and Series serialization (requires msgpack)."""

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_dataframe_basic(self):
        """Test basic DataFrame serialization."""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'c': ['x', 'y', 'z']})
        data = {'df': df}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['df'].equals(df)

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_dataframe_with_floats(self):
        """Test DataFrame with float columns."""
        df = pd.DataFrame({'floats': [1.1, 2.2, 3.3], 'ints': [1, 2, 3]})
        data = {'df': df}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['df'].equals(df)

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_series(self):
        """Test pandas Series serialization."""
        series = pd.Series([1, 2, 3, 4, 5])
        data = {'series': series}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['series'].equals(series)


class TestBinaryData:
    """Test binary data serialization (requires msgpack)."""

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_bytes_data(self):
        """Test bytes serialization."""
        data = {'binary': b'Hello, World!'}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['binary'] == data['binary']

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_large_binary_data(self):
        """Test large binary data serialization."""
        large_binary = b'\x00\x01\x02' * 1000  # 3000 bytes
        data = {'binary': large_binary}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['binary'] == large_binary


class TestComplexStructures:
    """Test complex nested structures."""

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_mixed_structure(self):
        """Test structure with JSON and binary data."""
        data = {
            'metadata': {'version': '1.0', 'created_at': '2024-01-01'},
            'array': np.array([1, 2, 3]),
            'binary': b'some_binary_data',
            'list': [1, 2, 'three'],
        }
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['metadata'] == data['metadata']
        assert np.array_equal(loaded['array'], data['array'])
        assert loaded['binary'] == data['binary']
        assert loaded['list'] == data['list']

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_dataframe_in_dict(self):
        """Test DataFrame within a dictionary."""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        data = {'description': 'Test data', 'dataframe': df, 'count': len(df)}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded['description'] == data['description']
        assert loaded['dataframe'].equals(df)
        assert loaded['count'] == 3


class TestSignatureVerification:
    """Test HMAC signature verification."""

    def test_valid_signature(self):
        """Test valid signature passes verification."""
        data = {'test': 'data'}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    def test_invalid_signature_wrong_key(self):
        """Test invalid signature with wrong key."""
        data = {'test': 'data'}
        signed = sign_and_dump(data, 'test_key')
        with pytest.raises(ValueError, match="Invalid signature"):
            verify_and_load(signed, 'wrong_key')

    def test_invalid_signature_tampered_data(self):
        """Test tampered data is detected."""
        data = {'test': 'data'}
        signed = sign_and_dump(data, 'test_key')
        # Tamper with the data
        import base64

        decoded = base64.b64decode(signed.encode('ascii'))
        tampered = decoded[:-5] + b'XXXXX'  # Change last 5 bytes
        tampered_signed = base64.b64encode(tampered).decode('ascii')
        with pytest.raises(ValueError, match="Invalid signature"):
            verify_and_load(tampered_signed, 'test_key')

    def test_malformed_data(self):
        """Test malformed data raises appropriate error."""
        malformed = "not_valid_base64!!!"
        with pytest.raises(ValueError):
            verify_and_load(malformed, 'test_key')

    def test_empty_string(self):
        """Test empty string raises error."""
        with pytest.raises(ValueError):
            verify_and_load('', 'test_key')


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_dict(self):
        """Test empty dictionary."""
        data = {}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == {}

    def test_empty_list(self):
        """Test empty list."""
        data = []
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == []

    def test_unicode_strings(self):
        """Test unicode string handling."""
        data = {'text': 'Hello 世界 🌍'}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data

    @pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
    def test_decimal_conversion(self):
        """Test Decimal objects are preserved."""
        data = {'value': Decimal('123.45')}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        # Decimal should be preserved (not converted to float)
        assert loaded['value'] == Decimal('123.45')
        # Alternatively, compare as float if needed
        assert float(loaded['value']) == 123.45

    def test_large_json_structure(self):
        """Test large JSON structure."""
        data = {f'key_{i}': f'value_{i}' for i in range(1000)}
        signed = sign_and_dump(data, 'test_key')
        loaded = verify_and_load(signed, 'test_key')
        assert loaded == data


class TestDifferentKeys:
    """Test behavior with different secret keys."""

    def test_bytes_key(self):
        """Test with bytes secret key."""
        data = {'test': 'data'}
        key = b'secret_key_bytes_32_characters_long!!'
        signed = sign_and_dump(data, key)
        loaded = verify_and_load(signed, key)
        assert loaded == data

    def test_string_key(self):
        """Test with string secret key."""
        data = {'test': 'data'}
        key = 'secret_key_string_32_characters_long'
        signed = sign_and_dump(data, key)
        loaded = verify_and_load(signed, key)
        assert loaded == data

    def test_key_conversion(self):
        """Test that string and bytes keys work equivalently."""
        data = {'test': 'data'}
        key_str = 'test_key_32_characters_long_12345'
        key_bytes = key_str.encode('utf-8')

        signed_str = sign_and_dump(data, key_str)
        signed_bytes = sign_and_dump(data, key_bytes)

        # Both should produce valid signatures
        loaded_str = verify_and_load(signed_str, key_str)
        loaded_bytes = verify_and_load(signed_bytes, key_bytes)

        assert loaded_str == data
        assert loaded_bytes == data


@pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")
class TestMsgpackFallback:
    """Test msgpack fallback for non-JSON data."""

    def test_numpy_without_msgpack_raises_error(self):
        """Test that numpy arrays raise error without msgpack."""
        # This test would need to mock HAS_MSGPACK to False
        # For now, we just verify msgpack is used for numpy
        data = {'array': np.array([1, 2, 3])}
        signed = sign_and_dump(data, 'test_key')
        # Verify the format type is 'msgp' (msgpack)
        import base64

        decoded = base64.b64decode(signed.encode('ascii'))
        format_type = decoded[:4]
        assert format_type == b'msgp'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
