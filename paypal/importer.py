from enum import Enum
from os import path
from typing import Any, List, Optional
from beancount.core import data, number
from beangulp.importers import csvbase
import csv as pycsv
from beancount.core.position import CostSpec
import datetime

english = {
    "date": "Date",
    "time": "Time",
    "timezone": "TimeZone",
    "name": "Name",
    "typ": "Type",
    "currency": "Currency",
    "amount": "Net",
    "balance": "Balance",
    "subject": "Subject",
    "bank_transfer": [
        "Bank Deposit to PP Account",
        "Algemene opname",
    ],  # TODO: < Translate
    "general_currency_conversion": "General Currency Conversion",
    "transaction_id": "Transaction ID",
    "reference_transaction_id": "Reference Txn ID",
}


class MergeType(Enum):
    BANK_TRANSFER = 0
    CURRENCY_CONVERSION = 1


pycsv.register_dialect("paypaldialect", delimiter=",")


class CommaAmount(csvbase.Column):
    def parse(self, value: str):
        return number.D(value.replace(",", "."))


class Importer(csvbase.Importer):
    encoding = "utf-8-sig"
    dialect = "paypaldialect"

    lang = english

    date = csvbase.Date(lang["date"], "%d/%m/%Y")
    payee = csvbase.Column(lang["name"])
    amount = CommaAmount(lang["amount"])
    currency = csvbase.Column(lang["currency"])
    balance_unreg = CommaAmount(lang["balance"])
    narration = csvbase.Column(lang["subject"])
    typ = csvbase.Column(lang["typ"])
    time = csvbase.Column(lang["time"])
    timezone = csvbase.Column(lang["timezone"])
    transaction_id = csvbase.Column(lang["transaction_id"])
    reference_transaction_id = csvbase.Column(lang["reference_transaction_id"])

    def __init__(
        self, base_currency: str, account: str, bank_account: Optional[str]
    ) -> None:
        self.bank_account = bank_account
        super().__init__(account, base_currency)

    def filename(self, filepath: str) -> str:
        return "paypal." + path.basename(filepath)

    def identify(remap, file: str) -> bool:
        f = open(file)
        is_correct = path.basename(f.name) == "Download.CSV"
        f.close()
        return is_correct

    def extract(self, filepath: str, existing: List[Any]) -> List[Any]:
        entries = super().extract(filepath, existing)
        read = self.read(filepath)

        iter = list(zip(entries, read))

        new_entries = []

        i = 0
        while i < len(iter):
            entry, row = iter[i]

            has_expense = len(entry.postings) == 2

            merges = []

            has_bank_transfer = False
            has_currency_conversion = False

            while i + 1 < len(iter):
                next_entry, next_row = iter[i + 1]
                if next_row.reference_transaction_id == row.transaction_id:

                    if next_row.typ in self.lang["bank_transfer"]:
                        merges.append(MergeType.BANK_TRANSFER)
                    elif next_row.typ == self.lang["general_currency_conversion"]:
                        merges.append(MergeType.CURRENCY_CONVERSION)
                    else:
                        print(
                            "unsupported transaction type that references a previous transaction:",
                            next_row.typ,
                        )

                    entry = entry._replace(
                        postings=entry.postings + next_entry.postings
                    )
                    i += 1

            # If there bank transfer immediately after, add this to the posting.
            # Later on, simplify to leave the account intact.
            # if i + 1 < len(iter):
            #    next_entry, next_row = iter[i + 1]
            #    if (
            #        next_row.typ in self.lang["bank_transfer"]
            #        and next_row.reference_transaction_id == row.transaction_id
            #    ):
            # Add the posting to the existing transaction.
            #        entry = entry._replace(
            #            postings=entry.postings + next_entry.postings
            #        )
            #        i += 1
            #        has_bank_transfer = True

            # Similarly for currency conversions
            # if i + 2 < len(iter):
            #    next_entry_1, next_row_1 = iter[i + 1]
            #    next_entry_2, next_row_2 = iter[i + 2]
            #    if (
            #        next_row_1.typ == self.lang["general_currency_conversion"]
            #        and next_row_2.typ == self.lang["general_currency_conversion"]
            #        and next_row.reference_transaction_id == row.transaction_id
            #    ):
            #        postings = [next_entry_1.postings[0], next_entry_2.postings[0]]

            #       if postings[0][1][1] != self.currency:
            #          postings = [entries[i + 1].postings[0], entries[i].postings[0]]

            #       cost_number_total = -postings[0][1][0]
            #       cost_currency = postings[0][1][1]
            #       postings[1] = postings[1]._replace(
            #           cost=CostSpec(
            #               None, cost_number_total, cost_currency, None, None, None
            #           )
            #       )

            #      entry = entry._replace(postings=entry.postings + postings)

            #    i += 2
            #       has_currency_conversion = True

            # Now we can have a single transaction with a lot of postings. Simplify.
            # if has_bank_transfer and (has_currency_conversion or has_expense):
            #    # First of all, try to see if added balance was removed immediately.
            #    new_balance_posting_index = len(new_entry.postings) - 4
            #    new_balance_remove_index = 0
            #    if has_currency_conversion:
            #        new_balance_remove_index = len(new_entry.postings) - 2
            #    new_entry = new_entry._replace(
            #        postings=[
            #            posting
            #            for (index, posting) in enumerate(new_entry.postings)
            #            if not index
            #            in [new_balance_posting_index, new_balance_remove_index]
            #        ]
            #    )

            # if has_currency_conversion and has_expense:
            # Now, move the cost spec to the actual expenses if the transaction is complete. The first and last entry should be removed, and the
            # cost should be moved from the last to the second (which will become the first.)
            #    first_index = 0
            #    last_index = len(new_entry.postings) - 1
            #    new_entry.postings[1] = new_entry.postings[1]._replace(
            #        cost=new_entry.postings[last_index][2]
            #   )
            #   new_entry = new_entry._replace(
            #       postings=[
            #           posting
            #           for (index, posting) in enumerate(new_entry.postings)
            #           if not index in [first_index, last_index]
            #       ]
            #   )

            # Add an expense posting from the first transaction.
            paypal_account_posting = entry.postings[0]
            first_entry = paypal_account_posting._replace(
                # TODO: For clarity, use Income when money is coming in.
                account="Expenses:UnknownAccount",
                units=-paypal_account_posting.units,
            )
            entry = entry._replace(postings=[first_entry] + entry.postings[1:])

            # If there was not a bank transfer, the money is coming from the paypal account. Add this posting (use the orinal posting).
            if not MergeType.BANK_TRANSFER in merges:
                entry = entry._replace(
                    postings=entry.postings[:1]
                    + [paypal_account_posting]
                    + entry.postings[1:]
                )

            # The first transaction is the primary transaction. The others should be merged
            while len(merges) > 0:
                if merges[-1] == MergeType.BANK_TRANSFER:
                    # The lowest posting is from a bank transfer. Invert the amount and add add a transfer posting.
                    amount = -entry.postings[-1].units
                    bank_transfer_posting = data.Posting(
                        self.bank_account,
                        amount,
                        None,
                        None,
                        None,
                        None,
                    )
                    entry = entry._replace(
                        postings=entry.postings[:-1] + [bank_transfer_posting]
                    )
                    merges = merges[:-1]
                elif merges[-1] == MergeType.CURRENCY_CONVERSION:
                    # Assume each currency conversion comes in pairs.
                    assert (
                        len(merges) >= 2 and merges[-2] == MergeType.CURRENCY_CONVERSION
                    )

                    # The bottom two postings correspond to the conversion.

                    # One currency gets subtracted, another added. Assume the second-last posting is the native currency.
                    # Other situations are probably possible, but not currently handled.
                    assert entry.postings[-2].units[1] == self.currency

                    # The first entry is the expense. See if the units is identical, in which case we can simply add the
                    # cost spec.
                    assert entry.postings[0].units == entry.postings[-1].units

                    # Add the cost spec
                    entry.postings[0] = entry.postings[0]._replace(
                        cost=CostSpec(
                            None,
                            -entry.postings[-2].units[0],
                            self.currency,
                            None,
                            None,
                            None,
                        )
                    )

                    # Remove the currency conversions.
                    entry = entry._replace(postings=entry.postings[:-2])

                    merges = merges[:-2]

            new_entries.append(entry)
            i += 1

        if len(iter) > 0:
            entry, row = iter[-1]
            if row.balance_unreg is not None:
                date = row.date + datetime.timedelta(days=1)
                units = data.Amount(row.balance_unreg, self.currency)
                meta = data.new_metadata(filepath, entry.meta["lineno"])
                new_entries.append(
                    data.Balance(meta, date, self.account(filepath), units, None, None)
                )

        return new_entries
