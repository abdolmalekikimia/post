from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import (
    assert_bag_result_contract,
    assert_label_content,
)
from assertions.connectivity_assertions import assert_error_codes_preserved, unverified_until_review
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    flush_unbagged_parcels,
    register_parcel,
    refresh_business_session,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step, FlowExecutionError, UnverifiedPreconditionError, raise_collected_failures
from utils.test_data import generated_barcode


@dataclass(frozen=True)
class LabelCase:
    case_id: str
    title: str
    category: str


@dataclass
class LabelResult:
    responses: dict[str, Any]
    report: ExecutionReport


LABEL_CASES = (
    LabelCase("S1", "Successful bag creation and barcode return", "success_bag"),
    LabelCase("S2", "Valid Base64 label generation and decoding", "label_format"),
    LabelCase("S3", "No eligible parcels yields NoEligibleParcels without label", "no_eligible"),
    LabelCase("S3b", "All parcels failed yields AllParcelsFailed without label", "all_failed"),
    LabelCase("S4", "Postal disconnection immediate error and destination release", "disconnection"),
    LabelCase("S5", "Partial failure generates label for successful parcels only", "partial_label"),
    LabelCase("S6", "Retry after success produces new bag barcode", "retry_success"),
    LabelCase("S7", "Immediate destination lock release verification after error", "lock_release_verify"),
    LabelCase("S8", "Label generation includes both new and deferred parcels", "mixed_deferred_label"),
)


def build_label_cases(
    run_settings: Settings = settings,
) -> tuple[LabelCase, ...]:
    return LABEL_CASES


def _fixture_barcode(run_settings: Settings, slot: int) -> str:
    prefix = os_barcode_prefix(run_settings)
    return generated_barcode(prefix, run_settings, slot)


def os_barcode_prefix(run_settings: Settings) -> str:
    return getattr(run_settings, "label_barcode_prefix", "830001")


def _case_chute(run_settings: Settings, case: LabelCase) -> str:
    base_chute = getattr(run_settings, "label_chute", "CH-04")
    return f"{base_chute}-{case.case_id}"


def _step(
    report: ExecutionReport,
    name: str,
    context: Any,
    action: Callable[[], Any],
    success_message: str,
) -> Any:
    report.register(name)
    return run_step(
        report,
        name,
        action,
        detail=lambda _: exchange_detail(context.ws.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(context.ws.last_exchange),
        },
        success_message=success_message,
    )


LABEL_FAULT_CATEGORIES = ("all_failed", "disconnection", "partial_label", "lock_release_verify", "mixed_deferred_label",
                          "error_code_fidelity", "error_code_mixed")
POSTAL_CONTRACTS_MIXED_CASE = LabelCase("F2", "PC-01 different codes in one bag stay on their own parcels", "error_code_mixed")
POSTAL_CONTRACTS_FIDELITY_CASE = LabelCase("F1", "PC-02 leading-zero and plain codes reach the device unchanged", "error_code_fidelity")
_NO_COUNTS = {"n": 0, "p": 0, "m": 0, "q": 0}


def _fault_fixture():
    from utils.postal_fault_fixture import ACTIVE
    return ACTIVE.get()


def _prepare_parcels(report: ExecutionReport, context: Any, run_settings: Settings,
                     case: LabelCase, barcodes: list[str], destination: str, chute: str) -> None:
    for index, bc in enumerate(barcodes, start=1):
        _step(report, f"[{case.case_id}] setup {index} Register parcel {bc}", context,
              lambda bc=bc: register_parcel(context.device, run_settings, bc),
              f"Parcel {bc} was registered.")
        wait_between_calls(run_settings)
        _step(report, f"[{case.case_id}] setup {index} Assign destination {bc}", context,
              lambda bc=bc: assign_parcel(context.device, bc, destination, chute),
              f"The destination of parcel {bc} was assigned.")
        wait_between_calls(run_settings)


def _fault_close(report: ExecutionReport, context: Any, run_settings: Settings,
                 name: str, destination: str, chute: str) -> dict[str, Any]:
    from utils.postal_fault_fixture import before_fault_close

    def action() -> dict[str, Any]:
        # Applies/removes the scoped adapter fault for this attempt first.
        before_fault_close(context, report)
        return close_bag(context.device, run_settings, destination, chute_ids=[chute])

    return _step(report, name, context, action, "The bag.close reply was received.")


def _assert_whole_postal_error(response: dict[str, Any], operation: str) -> None:
    from assertions.signalr_assertions import response_payload
    assert_bag_result_contract(response, expected_status=2, expected_result_type="Error",
                               expected_counts=_NO_COUNTS, expect_bag_identity_absent=True, operation=operation)
    payload = response_payload(response)
    assert str(payload.get("errorMessage") or "").strip(), f"{operation}: missing upstream error message"
    # edge-docs decisions.md (related item): a whole-request transport/Postal failure is resultType=Error; business codes
    # belong to per-parcel errors[], so a transport failure must not masquerade as one.
    assert not payload.get("errors"), f"{operation}: transport failure must not carry per-parcel business error codes"


def _assert_completed_with_label(response: dict[str, Any], destination: str, counts: dict[str, int],
                                 members: int, operation: str) -> dict[str, Any]:
    assert_bag_result_contract(response, expected_status=0, expected_result_type="Completed",
                               expected_counts=counts, expect_bag_identity=True, operation=operation)
    return assert_label_content(response, expected_destination=destination,
                                      expected_member_count=members, operation=operation)


def _run_fault_case(case: LabelCase, report: ExecutionReport, context: Any, run_settings: Settings,
                    destination: str, chute: str) -> dict[str, Any]:
    """Controlled Postal adapter faults; not proof of real Postal behaviour."""
    from utils.postal_fault_fixture import fixture_barcode
    fixture, op, cid = _fault_fixture(), f"label {case.case_id}", case.case_id
    category = case.category

    if category == "all_failed":
        barcodes = [fixture_barcode("830000", slot) for slot in (20, 21, 22)]
        _prepare_parcels(report, context, run_settings, case, barcodes, destination, chute)
        response = _fault_close(report, context, run_settings, f"[{cid}] Close bag - all parcels fail", destination, chute)
        assert_bag_result_contract(
            response, expected_status=0, expected_result_type="AllParcelsFailed",
            expected_counts={"n": 3, "p": 0, "m": 3, "q": 0}, expected_error_count=3,
            expected_error_barcodes=set(barcodes), expected_error_categories={"new"},
            expect_bag_identity_absent=True, operation=op)
        # PC-01: the adapter's own code reaches the device unchanged (fixture injects 9001).
        assert_error_codes_preserved(response, {bc: "9001" for bc in barcodes}, op)
        return response

    if category in ("disconnection", "lock_release_verify"):
        barcode = fixture_barcode("830000", 70)
        _prepare_parcels(report, context, run_settings, case, [barcode], destination, chute)
        first = _fault_close(report, context, run_settings, f"[{cid}] Close bag - Postal unavailable", destination, chute)
        _assert_whole_postal_error(first, f"{op} first attempt")
        fixture.verify_error_marker_cleared(report)
        if category == "disconnection":
            wait_between_calls(run_settings)
        retry = _fault_close(report, context, run_settings, f"[{cid}] Retry close on same destination", destination, chute)
        label = _assert_completed_with_label(retry, destination, {"n": 1, "p": 0, "m": 0, "q": 0}, 1, f"{op} recovery")
        return {"response": retry, "label": label}

    if category == "partial_label":
        barcodes = [fixture_barcode("830000", 1)] + [fixture_barcode("830000", slot) for slot in (2, 3)]
        _prepare_parcels(report, context, run_settings, case, barcodes, destination, chute)
        response = _fault_close(report, context, run_settings, f"[{cid}] Close bag - one parcel fails", destination, chute)
        assert_bag_result_contract(
            response, expected_status=0, expected_result_type="Completed",
            expected_counts={"n": 3, "p": 0, "m": 1, "q": 0}, expected_error_count=1,
            expected_error_barcodes={barcodes[0]}, expected_error_categories={"new"},
            expect_bag_identity=True, operation=op)
        label = assert_label_content(response, expected_destination=destination,
                                           expected_member_count=2, operation=op)
        return {"response": response, "label": label}

    if category == "mixed_deferred_label":
        deferred, fresh = fixture_barcode("830000", 10), fixture_barcode("830000", 11)
        _prepare_parcels(report, context, run_settings, case, [deferred], destination, chute)
        first = _fault_close(report, context, run_settings, f"[{cid}] First close - parcel deferred", destination, chute)
        assert_bag_result_contract(
            first, expected_status=0, expected_result_type="AllParcelsFailed",
            expected_counts={"n": 1, "p": 0, "m": 1, "q": 0}, expected_error_count=1,
            expected_error_barcodes={deferred}, expected_error_categories={"new"},
            expect_bag_identity_absent=True, operation=f"{op} first attempt")
        _prepare_parcels(report, context, run_settings, case, [fresh], destination, chute)
        second = _fault_close(report, context, run_settings, f"[{cid}] Second close - new and deferred", destination, chute)
        label = _assert_completed_with_label(second, destination, {"n": 1, "p": 1, "m": 0, "q": 0}, 2, f"{op} second attempt")
        return {"response": second, "label": label}

    if category == "error_code_fidelity":
        from utils.postal_fault_fixture import FIDELITY_CODES
        injected = {fixture_barcode("830000", slot): code for slot, code in FIDELITY_CODES.items()}
        _prepare_parcels(report, context, run_settings, case, list(injected), destination, chute)
        response = _fault_close(report, context, run_settings, f"[{cid}] Close bag - codes with and without leading zero", destination, chute)
        assert_bag_result_contract(
            response, expected_status=0, expected_result_type="AllParcelsFailed",
            expected_counts={"n": 2, "p": 0, "m": 2, "q": 0}, expected_error_count=2,
            expected_error_barcodes=set(injected), expected_error_categories={"new"},
            expect_bag_identity_absent=True, operation=op)
        # Type and digits are a hard contract: a string whose number is unchanged.
        assert_error_codes_preserved(response, injected, op, keep_leading_zeros=False)
        # Confirmed requirement (postal contracts answer 4): a leading zero is allowed and must be kept exactly.
        try:
            assert_error_codes_preserved(response, injected, op)
        except AssertionError as error:
            raise AssertionError(
                f"{error}; the exact code must be kept (confirmed requirement). Root cause seen on QA "
                "2026-11-03: Edge keeps the code in ParcelErrors.ErrorCode, an INTEGER column, so 0042 and 42 both become 42."
            ) from None
        return response

    if category == "error_code_mixed":
        from utils.postal_fault_fixture import MIXED_CODES
        injected = {fixture_barcode("830000", slot): code for slot, code in MIXED_CODES.items()}
        _prepare_parcels(report, context, run_settings, case, list(injected), destination, chute)
        response = _fault_close(report, context, run_settings, f"[{cid}] Close bag - three different codes", destination, chute)
        assert_bag_result_contract(
            response, expected_status=0, expected_result_type="AllParcelsFailed",
            expected_counts={"n": 3, "p": 0, "m": 3, "q": 0}, expected_error_count=3,
            expected_error_barcodes=set(injected), expected_error_categories={"new"},
            expect_bag_identity_absent=True, operation=op)
        # each barcode keeps ITS code: swapped or collapsed codes fail here
        assert_error_codes_preserved(response, injected, op)
        return response

    raise ValueError(f"Unknown label fault category: {category}")


def run_label_flow(
    run_settings: Settings = settings,
    cases: tuple[LabelCase, ...] | None = None,
) -> LabelResult:
    """Run label bag label generation and postal disconnect test cases."""
    selected_cases = cases or build_label_cases(run_settings)
    report = ExecutionReport("label label and disconnection flow")
    report.register(*PRECONDITION_STEPS)

    context = None
    destination = getattr(run_settings, "label_destination_code", "31417")
    failures = []
    responses: dict[str, Any] = {}

    try:
        slot = 1
        for case in selected_cases:
            try:
                if case.category in LABEL_FAULT_CATEGORIES and _fault_fixture() is None:
                    def missing():
                        raise UnverifiedPreconditionError(
                            f"label {case.case_id}: a controlled real Postal failure/deferred-member baseline and its independent evidence are required; a successful close cannot prove this scenario"
                        )
                    run_step(report, f"{case.case_id}: [PRECONDITION] Actual failure or mixed membership", missing,
                             mark_remaining_on_error=False)
                if context is None:
                    context = setup_authenticated_context(report, run_settings, "label")
                    if _fault_fixture() is None:
                        flush_unbagged_parcels(context.device, run_settings, (destination,))
                refresh_business_session(report, context.device, run_settings,
                                         f"label {case.case_id}")
                chute = _case_chute(run_settings, case)
                step_base = f"[{case.case_id}]"

                if case.category in ("success_bag", "label_format"):
                    bc = _fixture_barcode(run_settings, slot)
                    slot += 1
                    _step(
                        report,
                        f"5. {step_base} Register parcel",
                        context,
                        lambda bc=bc: register_parcel(context.device, run_settings, bc),
                        f"Parcel {case.case_id} was registered.",
                    )
                    wait_between_calls(run_settings)
                    _step(
                        report,
                        f"6. {step_base} Assign destination",
                        context,
                        lambda bc=bc: assign_parcel(
                            context.device,
                            bc,
                            destination,
                            chute,
                        ),
                        f"The destination of parcel {case.case_id} was assigned.",
                    )
                    wait_between_calls(run_settings)
                    response = _step(
                        report,
                        f"7. {step_base} Close bag",
                        context,
                        lambda: close_bag(
                            context.device,
                            run_settings,
                            destination,
                            chute_ids=[chute],
                        ),
                        f"Bag {case.case_id} was closed.",
                    )
                    assert_bag_result_contract(
                        response,
                        expected_status=0,
                        expected_result_type="Completed",
                        expected_counts={"n": 1, "p": 0, "m": 0, "q": 0},
                        expect_bag_identity=True,
                        operation=f"label {case.case_id}",
                    )
                    label_data = assert_label_content(
                        response,
                        expected_destination=destination,
                        expected_member_count=1,
                        operation=f"label {case.case_id}",
                    )
                    responses[case.case_id] = {
                        "response": response,
                        "label": label_data,
                    }

                elif case.category == "no_eligible":
                    # Clean destination with no eligible parcels
                    empty_chute = f"{chute}-empty"
                    response = _step(
                        report,
                        f"5. {step_base} Close bag on empty chute",
                        context,
                        lambda: close_bag(
                            context.device,
                            run_settings,
                            destination,
                            chute_ids=[empty_chute],
                        ),
                        "A close-bag request on an empty chute was sent.",
                    )
                    assert_bag_result_contract(
                        response,
                        expected_status=0,
                        expected_result_type="NoEligibleParcels",
                        expected_counts={"n": 0, "p": 0, "m": 0, "q": 0},
                        expect_bag_identity_absent=True,
                        operation=f"label {case.case_id}",
                    )
                    responses[case.case_id] = response

                elif case.category == "retry_success":
                    prior_barcodes = {
                        (value.get("response", value).get("payload", {}).get("bagBarcode"))
                        for value in responses.values() if isinstance(value, dict)
                        and value.get("response", value).get("payload", {}).get("resultType") == "Completed"
                    } - {None, ""}
                    if not prior_barcodes:
                        before_barcode = _fixture_barcode(run_settings, slot)
                        slot += 1
                        _step(report, f"5. {step_base} Create actual prior reading", context,
                              lambda: register_parcel(context.device, run_settings, before_barcode), "Prior read registered")
                        _step(report, f"6. {step_base} Assign actual prior reading", context,
                              lambda: assign_parcel(context.device, before_barcode, destination, chute), "Prior read assigned")
                        prior = _step(report, f"7. {step_base} Close actual prior bag", context,
                              lambda: close_bag(context.device, run_settings, destination, chute_ids=[chute]), "Prior close replied")
                        assert_bag_result_contract(prior, expected_status=0, expected_result_type="Completed",
                            expected_counts={"n":1,"p":0,"m":0,"q":0}, expect_bag_identity=True, operation="label S6 baseline")
                        prior_barcodes.add(prior["payload"]["bagBarcode"])
                    bc = _fixture_barcode(run_settings, slot)
                    slot += 1
                    _step(
                        report,
                        f"5. {step_base} Register new parcel after prior close",
                        context,
                        lambda bc=bc: register_parcel(context.device, run_settings, bc),
                        "A new parcel was registered after the previous bag was closed.",
                    )
                    wait_between_calls(run_settings)
                    _step(
                        report,
                        f"6. {step_base} Assign destination",
                        context,
                        lambda bc=bc: assign_parcel(
                            context.device,
                            bc,
                            destination,
                            chute,
                        ),
                        "The destination was assigned.",
                    )
                    wait_between_calls(run_settings)
                    response = _step(
                        report,
                        f"7. {step_base} Close bag again on same destination",
                        context,
                        lambda: close_bag(
                            context.device,
                            run_settings,
                            destination,
                            chute_ids=[chute],
                        ),
                        "The new bag was closed successfully.",
                    )
                    assert_bag_result_contract(
                        response,
                        expected_status=0,
                        expected_result_type="Completed",
                        expected_counts={"n": 1, "p": 0, "m": 0, "q": 0},
                        expect_bag_identity=True,
                        operation=f"label {case.case_id}",
                    )
                    def compare_bags():
                        after = response["payload"]["bagBarcode"]
                        assert after not in prior_barcodes, "New close reused a previous bag barcode"
                        return {"priorBagBarcodes": sorted(prior_barcodes), "newBagBarcode": after}
                    run_step(report, f"8. {step_base} Compare actual bag identities", compare_bags,
                             detail=lambda evidence: {"evidence": evidence}, mark_remaining_on_error=False)
                    responses[case.case_id] = response

                elif case.category in LABEL_FAULT_CATEGORIES:
                    responses[case.case_id] = _run_fault_case(case, report, context, run_settings, destination, chute)

                else:
                    raise ValueError(f"Unknown label category: {case.category}")
                wait_between_calls(run_settings)
            except FlowExecutionError as error:
                failures.append(error)
            except (AssertionError, ValueError) as error:
                def failed(error=error):
                    raise error
                try:
                    run_step(report, f"{case.case_id}: Verify actual contract", failed,
                        error_detail=lambda _: exchange_detail(context.ws.last_exchange) if context else {},
                        mark_remaining_on_error=False)
                except FlowExecutionError as wrapped:
                    failures.append(wrapped)

    finally:
        if context is not None:
            context.ws.close()
            context.rest_client.close()
        report.print()

    raise_collected_failures(failures)
    return LabelResult(responses=responses, report=report)
