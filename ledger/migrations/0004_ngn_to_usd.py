from django.db import migrations


def ngn_to_usd(apps, schema_editor):
    apps.get_model("ledger", "Account").objects.filter(currency="NGN").update(currency="USD")
    apps.get_model("ledger", "Transaction").objects.filter(currency="NGN").update(currency="USD")


def usd_to_ngn(apps, schema_editor):
    apps.get_model("ledger", "Account").objects.filter(currency="USD").update(currency="NGN")
    apps.get_model("ledger", "Transaction").objects.filter(currency="USD").update(currency="NGN")


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0003_transaction_destination_account_and_more"),
    ]

    operations = [
        migrations.RunPython(ngn_to_usd, usd_to_ngn),
    ]
