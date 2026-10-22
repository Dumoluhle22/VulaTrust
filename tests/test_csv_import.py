from pathlib import Path

import pytest

from app.csv_import import (
    MAX_FILE_BYTES, MAX_ROWS, check_csv, neutralise_formula,
)
from app.models import ApplicationSource, TriState

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "apps.csv"
HEADER = "app_name,vendor_domain,source,user_count,scopes,privileged\n"


def check(text: str, filename: str = "apps.csv"):
    return check_csv(text.encode("utf-8"), filename)


# ---- the sample file matches the documented expected results ---------------

@pytest.fixture(scope="module")
def sample_result():
    return check_csv(SAMPLE.read_bytes(), "apps.csv")


def test_sample_file_counts(sample_result):
    assert sample_result.file_error is None
    assert sample_result.rows_read == 23
    assert len(sample_result.valid) == 16
    assert len(sample_result.rejected) == 6
    assert len(sample_result.duplicates) == 1
    assert sample_result.blank_rows == 0


def test_sample_file_rejected_rows_have_line_numbers_and_reasons(sample_result):
    by_line = {row.line: row for row in sample_result.rejected}
    assert sorted(by_line) == [19, 20, 21, 22, 23, 24]
    assert by_line[19].reasons == ["User count must be a whole number."]
    assert by_line[20].reasons == ["User count must be 0 or more."]
    assert by_line[21].reasons == ["Source must be one of: manual, csv, google, microsoft."]
    assert by_line[22].reasons == ["Privileged must be yes, no or unknown."]
    assert by_line[23].reasons == ["Access description is too long (maximum 500 characters)."]
    assert by_line[24].reasons == ["App name is required."]


def test_sample_file_duplicate_points_at_the_first_row(sample_result):
    duplicate = sample_result.duplicates[0]
    assert (duplicate.line, duplicate.first_line) == (18, 2)
    assert duplicate.app_name == "PayTrack Payroll"


def test_sample_file_domains_are_cleaned(sample_result):
    domains = {row.app_name: row.vendor_domain for row in sample_result.valid}
    assert domains["PayTrack Payroll"] == "paytrack.example"
    assert domains["PayTrack Mobile"] == "paytrack.example"  # was PayTrack.example
    assert domains["ClinicNotes Web"] == "clinicnotes.example"  # was www.
    assert domains["QuickSign"] == "quicksign.example"  # was a full URL
    assert domains["ClinicNotes Reports"] == "app.clinicnotes.example"  # subdomain kept
    assert domains["Mystery PDF Tool"] is None  # blank domain


def test_sample_file_formula_row_is_neutralised_with_a_warning(sample_result):
    row = next(r for r in sample_result.valid if "Report Tool" in r.app_name)
    assert row.app_name == "'=1+1 Report Tool"
    assert row.line == 17
    assert any("formula" in text for _line, text in sample_result.warnings)


def test_sample_file_values_are_typed(sample_result):
    row = sample_result.valid[0]
    assert row.source == ApplicationSource.GOOGLE
    assert row.user_count == 3
    assert row.privileged == TriState.NO
    unknown = next(r for r in sample_result.valid if r.app_name == "ChatBridge Desktop")
    assert unknown.privileged == TriState.UNKNOWN


# ---- file-level checks -----------------------------------------------------

def test_wrong_extension_is_refused():
    assert "Only .csv files" in check(HEADER, "apps.txt").file_error
    assert "Only .csv files" in check(HEADER, "apps.csv.exe").file_error
    assert check(HEADER, "APPS.CSV").file_error is None


def test_too_large_file_is_refused():
    result = check_csv(b"x" * (MAX_FILE_BYTES + 1), "apps.csv")
    assert "too large" in result.file_error


def test_too_many_rows_is_refused():
    body = HEADER + "App,a.example,csv,1,x,no\n" * (MAX_ROWS + 1)
    assert "more than 5,000 rows" in check(body).file_error


def test_empty_and_whitespace_files_are_refused():
    assert check("").file_error == "The file is empty."
    assert check("  \n\n ").file_error == "The file is empty."


def test_binary_and_non_utf8_files_are_refused():
    assert "text CSV" in check_csv(b"PK\x03\x04\x00\x00binary", "apps.csv").file_error
    assert "UTF-8" in check_csv("naïve,é\n".encode("cp1252"), "apps.csv").file_error


def test_missing_columns_are_named():
    result = check("app_name,source\nApp,csv\n")
    assert result.file_error.startswith("Missing required columns: vendor_domain, user_count, scopes, privileged.")


def test_header_is_case_and_space_insensitive_and_extra_columns_are_ignored():
    text = " APP_NAME , Vendor_Domain,SOURCE,user_count,scopes,Privileged,extra\nApp,a.example,CSV,2,x,YES,ignored\n"
    result = check(text)
    assert result.file_error is None
    row = result.valid[0]
    assert (row.source, row.privileged, row.user_count) == (ApplicationSource.CSV, TriState.YES, 2)


def test_utf8_bom_from_excel_is_accepted():
    data = ("\ufeff" + HEADER + "App,a.example,csv,1,x,no\n").encode("utf-8")
    assert len(check_csv(data, "apps.csv").valid) == 1


def test_semicolon_separated_files_are_accepted():
    text = "app_name;vendor_domain;source;user_count;scopes;privileged\nApp;a.example;google;4;calendar, files;no\n"
    result = check(text)
    assert result.file_error is None
    assert result.valid[0].scopes == "calendar, files"


def test_header_only_file_has_no_rows_and_no_error():
    result = check(HEADER)
    assert result.file_error is None
    assert result.rows_read == 0


# ---- row-level checks ------------------------------------------------------

def test_blank_rows_are_skipped_and_counted():
    result = check(HEADER + "\nApp,a.example,csv,1,x,no\n,,,,,\n\n")
    assert result.rows_read == 1
    assert result.blank_rows == 3


def test_wrong_number_of_cells_is_rejected_with_a_hint():
    result = check(HEADER + "App,a.example,csv,1,calendar,files,no\nShort,a.example\n")
    assert [r.line for r in result.rejected] == [2, 3]
    assert "Expected 6 columns but found 7" in result.rejected[0].reasons[0]
    assert "quotes" in result.rejected[0].reasons[0]


def test_every_problem_in_a_row_is_reported_not_just_the_first():
    result = check(HEADER + ",a.example,dropbox,abc,x,maybe\n")
    assert result.rejected[0].reasons == [
        "App name is required.",
        "Source must be one of: manual, csv, google, microsoft.",
        "User count must be a whole number.",
        "Privileged must be yes, no or unknown.",
    ]


def test_blank_optional_cells_get_safe_defaults():
    row = check(HEADER + "App,,,,,\n").valid[0]
    assert row.vendor_domain is None
    assert row.source == ApplicationSource.CSV
    assert row.user_count == 0
    assert row.privileged == TriState.UNKNOWN  # missing is never treated as "no"
    assert row.scopes is None


@pytest.mark.parametrize("value", ["12.5", "1,000", "１２", "1e3", "0x10", " - 3"])
def test_user_count_must_be_ascii_digits(value):
    result = check(HEADER + f'App,a.example,csv,"{value}",x,no\n')
    assert len(result.rejected) == 1


def test_user_count_limits():
    assert len(check(HEADER + "App,a.example,csv,1000000,x,no\n").valid) == 1
    over = check(HEADER + "App,a.example,csv,1000001,x,no\n")
    assert over.rejected[0].reasons == ["User count must be 1,000,000 or less."]


def test_length_limits_sit_exactly_on_the_boundary():
    ok = check(HEADER + f"{'n' * 200},a.example,csv,1,{'s' * 500},no\n")
    assert len(ok.valid) == 1
    bad = check(HEADER + f"{'n' * 201},a.example,csv,1,{'s' * 501},no\n")
    assert len(bad.rejected[0].reasons) == 2


def test_long_names_are_shortened_in_the_rejected_report():
    result = check(HEADER + f"{'n' * 300},a.example,csv,1,x,no\n")
    assert len(result.rejected[0].app_name) <= 80


def test_invalid_domain_keeps_the_row_unassigned_with_a_warning():
    result = check(HEADER + "App,not a domain,csv,1,x,no\n")
    row = result.valid[0]
    assert row.vendor_domain is None
    assert "not valid" in row.warnings[0]


@pytest.mark.parametrize("start", ["=", "+", "-", "@"])
def test_formula_characters_are_neutralised_in_text_cells(start):
    result = check(HEADER + f'{start}cmd,a.example,csv,1,"{start}danger",no\n')
    row = result.valid[0]
    assert row.app_name == f"'{start}cmd"
    assert row.scopes == f"'{start}danger"
    assert len(row.warnings) == 2


def test_leading_spaces_do_not_hide_a_formula():
    row = check(HEADER + '"  =HYPERLINK(""x"")",a.example,csv,1,x,no\n').valid[0]
    assert row.app_name.startswith("'=")


def test_normal_text_is_left_alone():
    assert neutralise_formula("Plain app") == ("Plain app", False)
    assert neutralise_formula("") == ("", False)
    assert neutralise_formula("a=b") == ("a=b", False)


def test_duplicates_ignore_case_and_domain_formatting_but_not_source():
    text = HEADER + (
        "Payroll,paytrack.example,google,1,x,no\n"
        "payroll ,https://WWW.PayTrack.example/x,google,9,y,yes\n"
        "Payroll,paytrack.example,microsoft,1,x,no\n"
    )
    result = check(text)
    assert len(result.valid) == 2
    assert [(d.line, d.first_line) for d in result.duplicates] == [(3, 2)]


def test_a_rejected_row_never_counts_as_the_first_of_a_duplicate():
    text = HEADER + "App,a.example,dropbox,1,x,no\nApp,a.example,google,1,x,no\n"
    result = check(text)
    assert len(result.valid) == 1
    assert result.duplicates == []


def test_line_numbers_are_right_after_a_multi_line_quoted_cell():
    text = HEADER + '"Line\nbreak",a.example,csv,1,x,no\n,b.example,csv,1,x,no\n'
    result = check(text)
    assert len(result.valid) == 1
    assert result.rejected[0].line == 4  # header is line 1; the first record spans 2-3


def test_cells_are_plain_text_and_never_evaluated():
    text = HEADER + '__import__("os").system("echo hi"),a.example,csv,1,"{{ 7*7 }}",no\n'
    row = check(text).valid[0]
    assert row.app_name == '__import__("os").system("echo hi")'
    assert row.scopes == "{{ 7*7 }}"
