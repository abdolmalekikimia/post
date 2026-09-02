from config.settings import Settings
from utils.site_codes import (
    VALID_EXCHANGE_CENTER_CODES,
    configured_or_random_exchange_center_code,
)


def test_invalid_configured_exchange_center_is_replaced_with_valid_code():
    code = configured_or_random_exchange_center_code("11111")

    assert code in VALID_EXCHANGE_CENTER_CODES


def test_configured_valid_exchange_center_is_preserved():
    assert configured_or_random_exchange_center_code("10003") == "10003"


def test_settings_keeps_flow_destinations_valid_and_distinct():
    run_settings = Settings(
        destination_assignment_destination_code="11111",
        destination_assignment_second_destination_code="11111",
        destination_update_initial_destination_code="11111",
        destination_update_new_destination_code="22222",
        destination_update_closed_destination_code="33333",
        container_selection_destination_code="11111",
        container_selection_second_destination_code="22222",
    )

    destinations = (
        run_settings.destination_assignment_destination_code,
        run_settings.destination_assignment_second_destination_code,
        run_settings.destination_update_initial_destination_code,
        run_settings.destination_update_new_destination_code,
        run_settings.destination_update_closed_destination_code,
        run_settings.container_selection_destination_code,
        run_settings.container_selection_second_destination_code,
    )

    assert all(code in VALID_EXCHANGE_CENTER_CODES for code in destinations)
    assert (
        run_settings.destination_assignment_destination_code
        != run_settings.destination_assignment_second_destination_code
    )
    assert len(
        {
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_new_destination_code,
            run_settings.destination_update_closed_destination_code,
        }
    ) == 3
