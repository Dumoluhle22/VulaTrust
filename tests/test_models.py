import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    AgreementStatus,
    Application,
    ApplicationSource,
    HostingLocation,
    ImportBatch,
    TriState,
    Vendor,
)


def test_vendor_defaults_to_unknown(db):
    vendor = Vendor(name="Example Scheduler", primary_domain="examplescheduler.com")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    assert vendor.handles_personal_info == TriState.UNKNOWN
    assert vendor.hosting_location == HostingLocation.UNKNOWN
    assert vendor.operator_agreement_status == AgreementStatus.UNKNOWN
    assert vendor.owner is None
    assert vendor.last_reviewed is None


def test_enum_values_are_stored_as_plain_strings(db):
    vendor = Vendor(
        name="Example Files",
        handles_personal_info=TriState.YES,
        hosting_location=HostingLocation.OUTSIDE_SOUTH_AFRICA,
        operator_agreement_status=AgreementStatus.SIGNED,
    )
    db.add(vendor)
    db.commit()

    row = db.connection().exec_driver_sql(
        "SELECT handles_personal_info, hosting_location, operator_agreement_status "
        "FROM vendors"
    ).one()
    assert tuple(row) == ("yes", "outside_south_africa", "signed")


def test_primary_domain_must_be_unique(db):
    db.add(Vendor(name="A", primary_domain="same.com"))
    db.commit()
    db.add(Vendor(name="B", primary_domain="same.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_several_vendors_may_have_no_domain(db):
    db.add_all([Vendor(name="A"), Vendor(name="B")])
    db.commit()
    assert db.query(Vendor).count() == 2


def test_application_without_vendor_is_unassigned(db):
    app_row = Application(name="Mystery App")
    db.add(app_row)
    db.commit()
    db.refresh(app_row)

    assert app_row.vendor_id is None
    assert app_row.privileged == TriState.UNKNOWN
    assert app_row.source == ApplicationSource.MANUAL
    assert app_row.user_count == 0


def test_vendor_and_applications_are_linked(db):
    vendor = Vendor(name="Example Files", primary_domain="examplefiles.io")
    vendor.applications.append(Application(name="File Share"))
    vendor.applications.append(Application(name="File Share Mobile"))
    db.add(vendor)
    db.commit()

    assert len(vendor.applications) == 2
    assert all(a.vendor is vendor for a in vendor.applications)


def test_deleting_a_vendor_leaves_applications_unassigned(db):
    vendor = Vendor(name="Example Files")
    application = Application(name="File Share", vendor=vendor)
    db.add_all([vendor, application])
    db.commit()

    db.delete(vendor)
    db.commit()
    db.refresh(application)

    assert application.vendor_id is None
    assert db.query(Application).count() == 1


def test_negative_user_count_is_rejected(db):
    db.add(Application(name="Bad App", user_count=-1))
    with pytest.raises(IntegrityError):
        db.commit()


def test_import_batch_links_applications(db):
    batch = ImportBatch(filename="apps.csv", row_count=2)
    batch.applications.extend(
        [
            Application(name="One", source=ApplicationSource.CSV),
            Application(name="Two", source=ApplicationSource.CSV),
        ]
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    assert batch.matched_count == 0
    assert batch.rejected_count == 0
    assert {a.name for a in batch.applications} == {"One", "Two"}
