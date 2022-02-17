from beangulp_coinbase import importer

from beancount.parser import cmptest
from beancount.utils.test_utils import docfile
from beangulp import extract


class StringOutput:
    def __init__(self) -> None:
        self.s = ""

    def write(self, s: str):
        self.s = self.s + s

    def get(self) -> str:
        self.s


class TestCoinbase(cmptest.TestCase):
    @docfile
    def test_conversion(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Convert,CLV,2.500,EUR,1.0000,2.5000,2.5200,0.020000,Converted 2.500 CLV to 2.0000 DAI
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Converted 2.500 CLV to 2.0000 DAI"
  Assets:Coinbase:CLV     -2.500 CLV {} @ 1.0000 EUR
  Assets:Coinbase:DAI     2.0000 DAI {# 2.5000 EUR}
  Expenses:TradingFees  0.020000 EUR


""",
        )

    @docfile
    def test_earn(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Coinbase Earn,JASMY,20.000,EUR,4.5723,1.5638,1.5638,0.00,Received 20.00000 JASMY from Coinbase Earn
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Received 20.00000 JASMY from Coinbase Earn"
  Assets:Coinbase:JASMY   20.000 JASMY {# 1.5638 EUR} @ 4.5723 EUR
  Income:CoinbaseEarn    -1.5638 EUR


""",
        )

    @docfile
    def test_receive(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Receive,BTC,123.45678,EUR,10000.00,"","","",Received 123.45678 BTC from an external account
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Received 123.45678 BTC from an external account"
  Assets:Coinbase:BTC  123.45678 BTC {10000.00 EUR}


""",
        )

    @docfile
    def test_send(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Send,BTC,0.00123467,EUR,10123.00,"","","",Sent 0.00123467 BTC to 12345678901234567890
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Sent 0.00123467 BTC to 12345678901234567890"
  Assets:Coinbase:BTC  -0.00123467 BTC {} @ 10123.00 EUR


""",
        )

    @docfile
    def test_buy(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Buy,ETH,1.23456789,EUR,2000.00,30.00,31.99,1.99,Bought 1.23456789 ETH for €31.99 EUR
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Bought 1.23456789 ETH for €31.99 EUR"
  Assets:Coinbase:ETH   1.23456789 ETH {# 30.00 EUR} @ 2000.00 EUR
  Assets:Coinbase:EUR       -31.99 EUR
  Expenses:TradingFees        1.99 EUR


""",
        )

    @docfile
    def test_sell(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Sell,ETH,1.000000,EUR,1234.32,100.00,102.00,2.00,Sold 1.000000 ETH for €100.00 EUR
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Sold 1.000000 ETH for €100.00 EUR"
  Assets:Coinbase:ETH   -1.000000 ETH {} @ 1234.32 EUR
  Income:PL
  Assets:Coinbase:EUR      102.00 EUR
  Expenses:TradingFees       2.00 EUR


""",
        )

    @docfile
    def test_rewards_income(self, filename: str) -> None:
        """\
"You can use this transaction report to inform your likely tax obligations. For US customers, Sells, Converts, and Rewards Income, and Coinbase Earn transactions are taxable events. For final tax obligations, please consult your tax advisor."



Transactions
User,email@address.com,0000000000

Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,Spot Price at Transaction,Subtotal,Total (inclusive of fees),Fees,Notes
2022-01-28T00:00:00Z,Rewards Income,DAI,2.000000,EUR,0.8800000,1.760000,1.760000,0.000000,Received 1.000000 DAI from Coinbase Rewards
"""
        coinbase_importer = importer.Importer(
            coinbase_assets_base="Assets:Coinbase",
            earn_income_account="Income:CoinbaseEarn",
            pl_income_account="Income:PL",
            fees_expenses="Expenses:TradingFees",
            rewards_income_account="Income:CoinbaseRewards",
        )
        entries = coinbase_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2022-01-28 * "Received 1.000000 DAI from Coinbase Rewards"
  Assets:Coinbase:DAI      2.000000 DAI {# 1.760000 EUR} @ 0.8800000 EUR
  Income:CoinbaseRewards  -2.000000 DAI {# 1.760000 EUR}


""",
        )
