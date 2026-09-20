from config.settings import Settings
from utils.test_data import numeric_barcode


def test_numeric_barcode_is_unique_for_each_run_slot():
    run_settings = Settings(
        unique_run_data=True,
        test_run_id="123456",
    )

    first = numeric_barcode("123456789012345678901234", run_settings, slot=1)
    second = numeric_barcode("123456789012345678901234", run_settings, slot=2)

    assert len(first) == 24
    assert first.isdigit()
    assert len(second) == 24
    assert second.isdigit()
    # With unique_run_data=True and same prefix, different slots should give different suffixes
    assert first != second


def test_numeric_barcode_can_preserve_a_fixture_barcode():
    run_settings = Settings(
        unique_run_data=False,
        test_run_id="123456",
    )

    # With unique_run_data=False, it returns the numeric part of the barcode padded to 23 digits + Luhn check digit
    result = numeric_barcode("fixture-001", run_settings)
    assert result == "001000000000000000000008"
