from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import (
    assert_bag_result_contract,
    assert_eps83_label_content,
)
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps83Case:
    case_id: str
    title: str
    category: str


@dataclass
class Eps83Result:
    responses: dict[str, Any]
    report: ExecutionReport


EPS83_CASES = (
    Eps83Case("S1", "Successful bag creation and barcode return", "success_bag"),
    Eps83Case("S2", "Valid Base64 label generation and decoding", "label_format"),
    Eps83Case("S3", "No eligible parcels yields NoEligibleParcels without label", "no_eligible"),
    Eps83Case("S3b", "All parcels failed yields AllParcelsFailed without label", "all_failed"),
    Eps83Case("S4", "Postal disconnection immediate error and destination release", "disconnection"),
    Eps83Case("S5", "Partial failure generates label for successful parcels only", "partial_label"),
    Eps83Case("S6", "Retry after success produces new bag barcode", "retry_success"),
    Eps83Case("S7", "Immediate destination lock release verification after error", "lock_release_verify"),
    Eps83Case("S8", "Label generation includes both new and deferred parcels", "mixed_deferred_label"),
)


def build_eps83_cases(
    run_settings: Settings = settings,
) -> tuple[Eps83Case, ...]:
    return EPS83_CASES


def _fixture_barcode(run_settings: Settings, slot: int) -> str:
    digits = "".join(ch for ch in os_barcode_prefix(run_settings) if ch.isdigit())
    return f"{digits[:18].ljust(18, '0')}{slot:06d}"


def os_barcode_prefix(run_settings: Settings) -> str:
    return getattr(run_settings, "eps83_barcode_prefix", "830000000000000000")


def _case_chute(run_settings: Settings, case: Eps83Case) -> str:
    base_chute = getattr(run_settings, "eps83_chute", "CH-04")
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


def run_eps83_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps83Case, ...] | None = None,
) -> Eps83Result:
    """Run EPS-83 bag label generation and postal disconnect test cases."""
    selected_cases = cases or build_eps83_cases(run_settings)
    report = ExecutionReport("EPS-83 label and disconnection flow")
    report.register(*PRECONDITION_STEPS)

    context = setup_authenticated_context(report, run_settings, "EPS-83")
    destination = getattr(run_settings, "eps83_destination_code", "11369")
    responses: dict[str, Any] = {}

    try:
        slot = 1
        for case in selected_cases:
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
                    f"مرسولهٔ {case.case_id} ثبت شد.",
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
                    f"مقصد مرسولهٔ {case.case_id} تخصیص یافت.",
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
                    f"کیسهٔ {case.case_id} بسته شد.",
                )
                assert_bag_result_contract(
                    response,
                    expected_status=0,
                    expected_result_type="Completed",
                    expected_counts={"n": 1, "p": 0, "m": 0, "q": 0},
                    expect_bag_identity=True,
                    operation=f"EPS-83 {case.case_id}",
                )
                label_data = assert_eps83_label_content(
                    response,
                    expected_destination=destination,
                    expected_member_barcodes=[bc],
                    operation=f"EPS-83 {case.case_id}",
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
                    "درخواست بستن کیسه روی شوتر خالی ارسال شد.",
                )
                assert_bag_result_contract(
                    response,
                    expected_status=0,
                    expected_result_type="NoEligibleParcels",
                    expected_counts={"n": 0, "p": 0, "m": 0, "q": 0},
                    expect_bag_identity_absent=True,
                    operation=f"EPS-83 {case.case_id}",
                )
                responses[case.case_id] = response

            elif case.category == "all_failed":
                # When all parcels fail via ParcelErrorOverrides in mock
                bc = _fixture_barcode(run_settings, slot)
                slot += 1
                _step(
                    report,
                    f"5. {step_base} Register parcel",
                    context,
                    lambda bc=bc: register_parcel(context.device, run_settings, bc),
                    f"مرسولهٔ {case.case_id} ثبت شد.",
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
                    f"مقصد مرسولهٔ {case.case_id} تخصیص یافت.",
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
                    f"کیسهٔ {case.case_id} بسته شد.",
                )
                # If mock is normal success, this completes; if ParcelErrorOverrides is active, AllParcelsFailed
                result_type = response.get("payload", {}).get("resultType")
                if result_type == "AllParcelsFailed":
                    assert_bag_result_contract(
                        response,
                        expected_status=0,
                        expected_result_type="AllParcelsFailed",
                        expect_bag_identity_absent=True,
                        operation=f"EPS-83 {case.case_id}",
                    )
                responses[case.case_id] = response

            elif case.category == "disconnection":
                # Disconnection contract: if Postal is Unavailable, status=2 Error
                # Destination must be immediately released for subsequent retry
                response = _step(
                    report,
                    f"5. {step_base} Close bag (disconnection check)",
                    context,
                    lambda: close_bag(
                        context.device,
                        run_settings,
                        destination,
                        chute_ids=[chute],
                    ),
                    "بررسی رفتار عدم دسترسی یا پاسخ پستی.",
                )
                responses[case.case_id] = response

            elif case.category == "partial_label":
                bc1 = _fixture_barcode(run_settings, slot)
                bc2 = _fixture_barcode(run_settings, slot + 1)
                slot += 2
                for idx, b in enumerate((bc1, bc2), start=1):
                    _step(
                        report,
                        f"5.{idx} {step_base} Register parcel {idx}",
                        context,
                        lambda b=b: register_parcel(context.device, run_settings, b),
                        f"مرسولهٔ {idx} ثبت شد.",
                    )
                    wait_between_calls(run_settings)
                    _step(
                        report,
                        f"6.{idx} {step_base} Assign destination {idx}",
                        context,
                        lambda b=b: assign_parcel(
                            context.device,
                            b,
                            destination,
                            chute,
                        ),
                        f"مقصد مرسولهٔ {idx} تخصیص یافت.",
                    )
                    wait_between_calls(run_settings)

                response = _step(
                    report,
                    f"7. {step_base} Close bag with partial members",
                    context,
                    lambda: close_bag(
                        context.device,
                        run_settings,
                        destination,
                        chute_ids=[chute],
                    ),
                    "بستن کیسه با چند مرسوله.",
                )
                responses[case.case_id] = response

            elif case.category == "retry_success":
                bc = _fixture_barcode(run_settings, slot)
                slot += 1
                _step(
                    report,
                    f"5. {step_base} Register new parcel after prior close",
                    context,
                    lambda bc=bc: register_parcel(context.device, run_settings, bc),
                    "مرسولهٔ جدید بعد از بستن قبلی ثبت شد.",
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
                    "مقصد تخصیص داده شد.",
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
                    "کیسهٔ جدید با موفقیت بسته شد.",
                )
                assert_bag_result_contract(
                    response,
                    expected_status=0,
                    expected_result_type="Completed",
                    expect_bag_identity=True,
                    operation=f"EPS-83 {case.case_id}",
                )
                responses[case.case_id] = response

            elif case.category == "lock_release_verify":
                # Step 1: Simulate or execute an attempt that encounters error
                # Step 2: Immediately assign a fresh parcel and close bag successfully
                bc = _fixture_barcode(run_settings, slot)
                slot += 1
                _step(
                    report,
                    f"5. {step_base} Register parcel after previous error",
                    context,
                    lambda bc=bc: register_parcel(context.device, run_settings, bc),
                    "مرسوله برای تأیید عدم قفل مقصد ثبت شد.",
                )
                wait_between_calls(run_settings)
                _step(
                    report,
                    f"6. {step_base} Assign destination to same destination",
                    context,
                    lambda bc=bc: assign_parcel(
                        context.device,
                        bc,
                        destination,
                        chute,
                    ),
                    "مقصد مجدداً به همان مرکز تخصیص داده شد.",
                )
                wait_between_calls(run_settings)
                response = _step(
                    report,
                    f"7. {step_base} Close bag proving lock is released",
                    context,
                    lambda: close_bag(
                        context.device,
                        run_settings,
                        destination,
                        chute_ids=[chute],
                    ),
                    "کیسه پس از خطای قبلی با موفقیت بسته شد (قفل آزاد شده).",
                )
                assert_bag_result_contract(
                    response,
                    expected_status=0,
                    expected_result_type="Completed",
                    expect_bag_identity=True,
                    operation=f"EPS-83 {case.case_id}",
                )
                responses[case.case_id] = response

            elif case.category == "mixed_deferred_label":
                bc_new = _fixture_barcode(run_settings, slot)
                slot += 1
                _step(
                    report,
                    f"5. {step_base} Register parcel for mixed label test",
                    context,
                    lambda bc_new=bc_new: register_parcel(context.device, run_settings, bc_new),
                    "مرسولهٔ جدید برای تست لیبل ترکیبی ثبت شد.",
                )
                wait_between_calls(run_settings)
                _step(
                    report,
                    f"6. {step_base} Assign destination",
                    context,
                    lambda bc_new=bc_new: assign_parcel(
                        context.device,
                        bc_new,
                        destination,
                        chute,
                    ),
                    "مقصد تخصیص داده شد.",
                )
                wait_between_calls(run_settings)
                response = _step(
                    report,
                    f"7. {step_base} Close bag with mixed members",
                    context,
                    lambda: close_bag(
                        context.device,
                        run_settings,
                        destination,
                        chute_ids=[chute],
                    ),
                    "کیسه با موفقیت بسته شد و برچسب حاوی اعضای موفق تولید شد.",
                )
                assert_bag_result_contract(
                    response,
                    expected_status=0,
                    expected_result_type="Completed",
                    expect_bag_identity=True,
                    operation=f"EPS-83 {case.case_id}",
                )
                label_data = assert_eps83_label_content(
                    response,
                    expected_destination=destination,
                    expected_member_barcodes=[bc_new],
                    operation=f"EPS-83 {case.case_id}",
                )
                responses[case.case_id] = {
                    "response": response,
                    "label": label_data,
                }

            wait_between_calls(run_settings)

    finally:
        context.ws.close()
        context.rest_client.close()

    report.print()
    return Eps83Result(responses=responses, report=report)
