#! Code voor een ASN betaalrekening

from os import path
from typing import Dict, Optional, Tuple
from beancount.core import data, number, position
from beangulp.importers import csvbase
import csv as pycsv
import re

pycsv.register_dialect("asnbankdialect", delimiter=",")


class Importer(csvbase.Importer):
    encoding = "utf8"
    names = False
    dialect = "asnbankdialect"


    def __init__(
        self,
        known_accounts: Dict[str, str],
        currency: str = "EUR",
        interest_account: Optional[str] = None,
        investment_account: Optional[str] = None,
        profit_loss_account: Optional[str] = None,
    ) -> None:
        self.known_accounts = known_accounts
        self.interest_account = interest_account
        self.investment_account = investment_account
        self.profit_loss_account = profit_loss_account
        self.columns = {
            "date": csvbase.Date(0, "%d-%m-%Y"),
            "own_account": csvbase.Column(1),
            "other_account": csvbase.Column(2),
            "payee": csvbase.Column(3),
            "amount": csvbase.Amount(10),
            "narration": csvbase.Column(17),
            "balance_before": csvbase.Amount(8),
            "booking_code": csvbase.Column(14),
        }
        super().__init__("ACCOUNT_PLACEHOLDER", currency)

    def filename(self, filepath) -> str:
        return "asnbank." + path.basename(filepath)

    def account(self, filepath: str) -> str:
        for row in self.read(filepath):
            return self.known_accounts[row.own_account]

    def identify(remap, file) -> bool:
        with open(file) as fd:
            head = fd.read(1024)
        return not re.search("^\d\d-\d\d-\d\d\d\d,", head) is None

    def extract(self, filepath, existing) -> data.Entries:
        entries = super().extract(filepath, existing)

        # Build a balance entry. The balance is not after but before, so this requires custom code.
        if len(entries) != 0:
            date = entries[-1].date
            (row, lineno) = next(
                (row, lineno)
                for lineno, row in enumerate(self.read(filepath))
                if row.date == date
            )
            units = data.Amount(row.balance_before, self.currency)
            meta = data.new_metadata(filepath, lineno)
            balance = data.Balance(
                meta, date, self.known_accounts[row.own_account], units, None, None
            )

            # Now insert at the correct location
            found_index = 0
            for index, value in enumerate(entries):
                if value.date == date:
                    found_index = index
                    break

            entries.insert(found_index, balance)

        return entries

    def finalize(self, transaction, row):
        # Set the account number
        transaction.postings[0] = transaction.postings[0]._replace(
            account=self.known_accounts[row.own_account]
        )

        # Fix extra quotes
        if transaction.narration != "GEEN":
            transaction = transaction._replace(narration=transaction.narration[1:-1])

        # Add known accounts as a posting
        if row.other_account in self.known_accounts.keys():
            transaction.postings.append(
                data.Posting(
                    self.known_accounts[row.other_account],
                    -transaction.postings[0].units,
                    None,
                    None,
                    None,
                    None,
                )
            )
        # Handle interest posting
        elif self.interest_account != None and row.booking_code == "RNT":
            transaction.postings.append(
                data.Posting(
                    self.interest_account,
                    -transaction.postings[0].units,
                    None,
                    None,
                    None,
                    None,
                )
            )

        # Aan-/verkoop beleggingen
        # TODO: Why not add a balance check. (Available in the narration.)
        elif (
            self.investment_account != None
            and self.profit_loss_account != None
            and row.booking_code == "EFF"
        ):
            regex = "^Voor\s+u\s+([a-z]+kocht)\s+via\s+Euronext\s+Fund\s+Services:\s+(\d+ \d+)\s+Participaties\s+(.*)\s+a\s+EUR\s+(\d+ \d+)."
            result = re.match(regex, transaction.narration)
            profit_loss = False
            if result != None:
                transaction_type = result.group(1)
                share_amount = number.D(result.group(2).replace(" ", "."))
                share_type = result.group(3).replace(" ", "")
                share_cost = number.D(result.group(4).replace(" ", "."))
                (
                    other_account,
                    share_currency,
                ) = self.get_investment_account_and_currency(share_type)
                price = None
                cost = None
                if transaction_type == "verkocht":
                    share_amount = -share_amount
                    price = data.Amount(share_cost, "EUR")
                    cost = position.CostSpec(None, None, None, None, None, None)
                    transaction = transaction._replace(narration="Verkoop beleggen")
                    profit_loss = True
                elif transaction_type == "gekocht":
                    cost = position.CostSpec(share_cost, None, "EUR", None, None, None)
                    transaction = transaction._replace(narration="Aankoop beleggen")
                else:
                    print("Warning: Unknown transaction type: " + transaction_type)

                other_amount = data.Amount(share_amount, share_currency)
                transaction.postings.append(
                    data.Posting(other_account, other_amount, cost, price, None, None)
                )

            if profit_loss:
                transaction.postings.append(
                    data.Posting(self.profit_loss_account, None, None, None, None, None)
                )

        return transaction

    def get_investment_account_and_currency(self, share_type: str) -> Tuple[str, str]:
        if share_type == "ASNDuurzaamMixfondsZeerDefensief":
            other_account = self.investment_account + ":DuurzaamMixfondsZeerDefensief"
            share_currency = "ASN_MIXFONDS_ZEER_DEFENSIEF"
        elif share_type == "ASNDuurzaamMixfondsDefensief":
            other_account = self.investment_account + ":DuurzaamMixfondsDefensief"
            share_currency = "ASN_MIXFONDS_DEFENSIEF"
        elif share_type == "ASNDuurzaamMixfondsNeutraal":
            other_account = self.investment_account + ":DuurzaamMixfondsNeutraal"
            share_currency = "ASN_MIXFONDS_NEUTRAAL"
        elif share_type == "ASNDuurzaamMixfondsOffensief":
            other_account = self.investment_account + ":DuurzaamMixfondsOffensief"
            share_currency = "ASN_MIXFONDS_OFFENSIEF"
        elif share_type == "ASNDuurzaamMixfondsZeerOffensief":
            other_account = self.investment_account + ":DuurzaamMixfondsZeerOffensief"
            share_currency = "ASN_MIXFONDS_ZEER_OFFENSIEF"
        elif share_type == "ASNMilieu&Waterfonds":
            other_account = self.investment_account + ":MilieuEnWaterfonds"
            share_currency = "ASN_MILIEU_EN_WATERFONDS"
        elif share_type == "ASN-NovibMicrokredietfonds":
            other_account = self.investment_account + ":Microkredietfonds"
            share_currency = "ASN_MICROKREDIETFONDS"
        elif share_type == "ASNDuurzaamObligatiefonds":
            other_account = self.investment_account + ":Obligatiefonds"
            share_currency = "ASN_OBLIGATIEFONDS"
        elif share_type == "ASNMicrokredietfonds":
            other_account = self.investment_account + ":Microkredietfonds"
            share_currency = "ASN_MICROKREDIETFONDS"
        elif share_type == "ASNGroenprojectenfonds":
            other_account = self.investment_account + ":Groenprojectenfonds"
            share_currency = "ASN_GROENPROJECTENFONDS"
        else:
            print("Warning: Unknown share type: " + share_type)
        return [other_account, share_currency]
