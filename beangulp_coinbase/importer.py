from dataclasses import MISSING
from os import path
from beancount.core import data, number
from beancount.core.position import CostSpec, Cost
from beangulp.importers import csvbase
import csv as pycsv
import decimal
import re

pycsv.register_dialect("coinbasedialect", delimiter=",")


class PotentiallyEmptyAmount(csvbase.Column):
    def __init__(self, name, subs=None):
        super().__init__(name)
        self.subs = subs if subs is not None else {}

    def parse(self, value):
        for pattern, replacement in self.subs.items():
            value = re.sub(pattern, replacement, value)
        if value == "":
            return number.D("0.00")
        return decimal.Decimal(value)

class Importer(csvbase.Importer):
    encoding = "utf8"
    names = True
    dialect = "coinbasedialect"
    skiplines = 7

    date = csvbase.Date("Timestamp", "%Y-%m-%dT%H:%M:%SZ")
    amount = csvbase.Amount("Quantity Transacted")
    narration = csvbase.Column("Notes")
    currency = csvbase.Column("Asset")
    fees = PotentiallyEmptyAmount("Fees")
    transaction_type = csvbase.Column("Transaction Type")

    # Subtotal (Cost of transaction input)
    subtotal = PotentiallyEmptyAmount("Subtotal")
    total_with_fees = PotentiallyEmptyAmount("Total (inclusive of fees)")

    spot_price_currency = csvbase.Column("Spot Price Currency")
    spot_price_at_transaction = csvbase.Amount("Spot Price at Transaction")

    def __init__(
        self,
        coinbase_assets_base: str,
        earn_income_account: str,
        pl_income_account: str,
        fees_expenses: str,
        currency: str = "EUR",
    ) -> None:
        self.earn_income_account = earn_income_account
        self.pl_income_account = pl_income_account
        self.coinbase_assets_base = coinbase_assets_base
        self.fees_expenses = fees_expenses
        super().__init__(coinbase_assets_base, currency)

    def filename(self, filepath):
        return "coinbase." + path.basename(filepath)

    def identify(remap, file):
        with open(file) as fd:
            return path.basename(fd.name).startswith("Coinbase-")

    def coinbase_account_for_asset(self, asset: str) -> str:
        return self.coinbase_assets_base + ":" + asset

    def finalize(self, transaction, row):
        # Generate cost spec when necessary
        cost_spec = None
        price = None

        # Whether the primary transaction is an output
        negate = row.transaction_type in ["Sell", "Convert", "Send"]

        # If a price is available, use it
        if not row.spot_price_at_transaction.is_zero():
            price = data.Amount(row.spot_price_at_transaction, row.spot_price_currency)

        # For transactions where the primary is output, add an empty cost to automatically reduce
        if negate:
            cost_spec = CostSpec(None, None, None, None, None, None)
        # Otherwise, add the cost
        elif not row.total_with_fees.is_zero():
            # Use transaction value as total cost.
            # When using Buy, the primary is the output, so use the subtotal without fees.
            primary_cost = None
            if row.transaction_type == "Buy":
                primary_cost = row.subtotal
            else:
                primary_cost = row.total_with_fees
            cost_spec = CostSpec(None, primary_cost, row.spot_price_currency, None, None, None)
        # Finally, if we want a cost but it isn't available, use the spot price.
        # To avoid clutter, remove the price entry as it is identical.
        elif not row.spot_price_at_transaction.is_zero():
            price = None
            cost_spec = Cost(
                row.spot_price_at_transaction, row.spot_price_currency, None, None
            )

        # 1. Add currency to account name
        # 2. Add price and cost
        # 3. Negate if necessary
        amount = transaction.postings[0][1]
        prim_currency = amount[1]
        if negate:
            amount = -amount
        account_name = self.coinbase_account_for_asset(prim_currency)
        transaction.postings[0] = data.Posting(
            account_name, amount, cost_spec, price, None, None
        )

        if row.transaction_type == "Convert":
            # Determine the conversion to from the narration
            matches = re.search(
                "^Converted [0-9\.]+ [A-Z]+ to ([0-9\.]+) ([A-Z]+)$", row.narration
            )
            to_units = number.D(matches[1])
            to_currency = matches[2]
            to_amount = data.Amount(to_units, to_currency)
            to_cost_spec = CostSpec(None, row.subtotal, row.spot_price_currency, None, None, None)
            transaction.postings.append(
                data.Posting(
                    self.coinbase_account_for_asset(to_currency),
                    to_amount,
                    to_cost_spec,
                    None,
                    None,
                    None,
                )
            )
        elif row.transaction_type == "Coinbase Earn":
            # Add the earning in the base currency.
            transaction.postings.append(
                data.Posting(
                    self.earn_income_account,
                    -data.Amount(row.total_with_fees, row.spot_price_currency),
                    None,
                    None,
                    None,
                    None,
                )
            )
        elif row.transaction_type == "Sell":
            # HandelPL
            handel_pl = data.Posting(
                self.pl_income_account, None, None, None, None, None
            )
            transaction.postings.append(handel_pl)
            sold_for_posting = data.Posting(
                self.coinbase_account_for_asset(self.currency),
                data.Amount(row.total_with_fees, self.currency),
                None,
                None,
                None,
                None,
            )
            transaction.postings.append(sold_for_posting)
        elif row.transaction_type == "Buy":
            buy_with_posting = data.Posting(
                self.coinbase_account_for_asset(self.currency),
                -data.Amount(row.total_with_fees, self.currency),
                None,
                None,
                None,
                None,
            )
            transaction.postings.append(buy_with_posting)

        # Fees
        if not row.fees.is_zero():
            units = data.Amount(row.fees, self.currency)
            fee_posting = data.Posting(
                self.fees_expenses, units, None, None, None, None
            )
            transaction.postings.append(fee_posting)

        return transaction
