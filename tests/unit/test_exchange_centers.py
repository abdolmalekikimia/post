from config.settings import Settings
from utils.exchange_centers import (
    VALID_EXCHANGE_CENTER_CODES,
    configured_or_random_exchange_center_code,
)


def test_invalid_configured_exchange_center_is_replaced_with_valid_code():
    code = configured_or_random_exchange_center_code("11111")

    assert code in VALID_EXCHANGE_CENTER_CODES


def test_configured_valid_exchange_center_is_preserved():
    assert configured_or_random_exchange_center_code("71956") == "71956"


def test_settings_keeps_flow_destinations_valid_and_distinct():
    run_settings = Settings(
        eps71_destination_code="11111",
        eps71_second_destination_code="11111",
        eps73_initial_destination_code="11111",
        eps73_new_destination_code="22222",
        eps73_closed_destination_code="33333",
        eps76_destination_code="11111",
        eps76_second_destination_code="22222",
    )

    destinations = (
        run_settings.eps71_destination_code,
        run_settings.eps71_second_destination_code,
        run_settings.eps73_initial_destination_code,
        run_settings.eps73_new_destination_code,
        run_settings.eps73_closed_destination_code,
        run_settings.eps76_destination_code,
        run_settings.eps76_second_destination_code,
    )

    assert all(code in VALID_EXCHANGE_CENTER_CODES for code in destinations)
    assert (
        run_settings.eps71_destination_code
        != run_settings.eps71_second_destination_code
    )
    assert len(
        {
            run_settings.eps73_initial_destination_code,
            run_settings.eps73_new_destination_code,
            run_settings.eps73_closed_destination_code,
        }
    ) == 3
