from os import path
from turtle import pos
from typing import Optional
from beangulp.importers import csvbase
import csv as pycsv
from beancount.core import number, data

pycsv.register_dialect("ovchipkaartdialect", delimiter=";")


class CommaAmount(csvbase.Column):
    def parse(self, value):
        return number.D(value.replace(",", "."))


class Importer(csvbase.Importer):
    encoding = "utf8"
    names = True
    dialect = "ovchipkaartdialect"

    date = csvbase.Date("Datum", "%d-%m-%Y")
    amount = CommaAmount("Bedrag")
    narration = csvbase.Column("Transactie")
    starting_location = csvbase.Column("Vertrek")
    destination = csvbase.Column("Bestemming")
    product = csvbase.Column("Product")

    #! - account: The card account
    #! - bank_account: The bank account that money is subtracted from. Tip: Can be Liabilities:OvIncasso
    #! - currency: The currency.
    def __init__(
        self, account: str, bank_account: Optional[str], currency: str = "EUR"
    ) -> None:
        self.bank_account = bank_account
        super().__init__(account, currency)

    def filename(self, filepath):
        return "ovchipkaart." + path.basename(filepath)

    def extract(self, filepath, existing):
        return [
            entry
            for entry in super().extract(filepath, existing)
            if not entry.postings[0].units.number.is_zero()
        ]

    def identify(remap, file):
        header = '"Datum";"Check-in";"Vertrek";"Check-uit";"Bestemming";"Bedrag";"Transactie";"Klasse";"Product";"Opmerkingen";"Naam";"Kaartnummer"'
        with open(file) as fd:
            head = fd.read(len(header))
        return head.startswith(header)

    def finalize(self, transaction, row):
        if row.narration == "Saldo automatisch opgeladen":
            topup_at = row.destination  # Contains something like 'bij NS'
            transaction = transaction._replace(
                narration=transaction.narration + " " + topup_at
            )

            # We know what the other posting should be if it was supplied. Add it here.
            if not self.bank_account == None:
                transaction = transaction._replace(
                    postings=transaction.postings
                    + [
                        data.Posting(
                            self.bank_account,
                            -transaction.postings[0].units,
                            None,
                            None,
                            None,
                            None,
                        )
                    ]
                )
        else:
            if (
                row.starting_location == None
                or row.destination == None
                or row.product == None
            ):
                transaction = transaction._replace(narration=None)
            else:
                transaction = transaction._replace(
                    narration=row.starting_location
                    + " - "
                    + row.destination
                    + " - "
                    + row.product
                )

            amount = transaction.postings[0].units
            postings = transaction.postings
            postings[0] = postings[0]._replace(units=-amount)
            transaction = transaction._replace(postings=postings)

        return transaction
