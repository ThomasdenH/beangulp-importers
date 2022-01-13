from typing import Optional
from beangulp_paypal import importer

import unittest

from beancount.parser import cmptest, printer
from beancount.utils.test_utils import docfile


class TestPaypal(cmptest.TestCase):
    @docfile
    def test_basic_transaction(self, filename: str) -> None:
        """\
"Date","Time","TimeZone","Name","Type","Status","Currency","Gross","Fee","Net","From Email Address","To Email Address","Transaction ID","Reference Txn ID","Receipt ID","Balance","Subject"
"10/12/2020","13:54:37","PST","Payee","Express Checkout Payment","Completed","EUR","-30,00","0,00","-30,00","email@address.com","anotheremail@address.com","253285736","","","-30,00","Transaction subject"
        """
        paypal_importer = importer.Importer(
            "EUR", "Assets:Paypal", "Liabilities:DirectDebit"
        )
        entries = paypal_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """
            2020-12-10 * "Payee" "Transaction subject"
                Expenses:UnknownAccount   30.00 EUR
                Assets:Paypal            -30.00 EUR

            2020-12-11 balance Assets:Paypal                                   -30.00 EUR
        """,
        )

    # Paypal files contain no header if there are no entries
    @docfile
    def test_empty_file(self, filename) -> None:
        """ """
        paypal_importer = importer.Importer(
            "EUR", "Assets:Paypal", "Liabilities:DirectDebit"
        )
        entries = paypal_importer.extract(filename, [])
        self.assertEqualEntries(entries, "")

    @docfile
    def test_direct_bank_transfer(self, filename: str) -> None:
        """\
"Date","Time","TimeZone","Name","Type","Status","Currency","Gross","Fee","Net","From Email Address","To Email Address","Transaction ID","Reference Txn ID","Receipt ID","Balance","Subject"
"19/08/2020","03:00:00","PDT","Payee","Express Checkout Payment","Completed","EUR","-66,00","0,00","-66,00","email@address.com","anotheremail@address.com","transactionid23423","","","-66,00","Description"
"19/08/2020","03:00:00","PDT","","Bank Deposit to PP Account ","Pending","EUR","66,00","0,00","66,00","","email@address.com","6324872369","transactionid23423","","0,00","Another description"
        """
        paypal_importer = importer.Importer(
            "EUR", "Assets:Paypal", "Liabilities:DirectDebit"
        )
        entries = paypal_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """
            2020-08-19 * "Payee" "Description"
                Expenses:UnknownAccount   66.00 EUR
                Liabilities:DirectDebit  -66.00 EUR

            2020-08-20 balance Assets:Paypal                                   0.00 EUR
        """,
        )

    @docfile
    def test_currency_conversion(self, filename: str) -> None:
        """\
"Date","Time","TimeZone","Name","Type","Status","Currency","Gross","Fee","Net","From Email Address","To Email Address","Transaction ID","Reference Txn ID","Receipt ID","Balance","Subject"
"13/08/2019","07:00:00","PDT","Grocery Store","PreApproved Payment Bill User Payment","Completed","USD","-15,00","0,00","-15,00","email@address.com","anotheremail@address.com","transaction_id2343","63464334","","-15,00","An apple and an egg"
"13/08/2019","07:00:00","PDT","","Bank Deposit to PP Account ","Pending","EUR","13,92","0,00","13,92","","email@address.com","id1","transaction_id2343","","13,92","An apple and an egg"
"13/08/2019","07:00:00","PDT","","General Currency Conversion","Completed","EUR","-13,92","0,00","-13,92","email@address.com","","id2","transaction_id2343","","0,00","An apple and an egg"
"13/08/2019","07:00:00","PDT","","General Currency Conversion","Completed","USD","15,00","0,00","15,00","","email@address.com","id3","transaction_id2343","","0,00","An apple and an egg"
        """
        paypal_importer = importer.Importer(
            "EUR", "Assets:Paypal", "Liabilities:DirectDebit"
        )
        entries = paypal_importer.extract(filename, [])

        # For some reason comparing directly doesn't work
        actual = ""
        for entry in entries:
            actual = actual + printer.format_entry(entry)

        expected = """\
2019-08-13 * "Grocery Store" "An apple and an egg"
  Expenses:UnknownAccount   15.00 USD {# 13.92 EUR}
  Liabilities:DirectDebit  -13.92 EUR
2019-08-14 balance Assets:Paypal                                   0.00 EUR
"""

        self.assertEqual(actual, expected)

    @docfile
    def test_inheritance(self, filename: str) -> None:
        """\
"Date","Time","TimeZone","Name","Type","Status","Currency","Gross","Fee","Net","From Email Address","To Email Address","Transaction ID","Reference Txn ID","Receipt ID","Balance","Subject"
"10/12/2020","13:54:37","PST","Movie Distributor","Express Checkout Payment","Completed","EUR","-30,00","0,00","-30,00","email@address.com","anotheremail@address.com","253285736","","","-30,00","Transaction subject"
        """

        class Importer(importer.Importer):
            def finalize(self, txn, row):
                if row.payee == "Movie Distributor":
                    txn.postings[0] = txn.postings[0]._replace(
                        account="Expenses:Movies"
                    )
                return txn

        paypal_importer = Importer("EUR", "Assets:Paypal", "Liabilities:DirectDebit")
        entries = paypal_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """         
            2020-12-10 * "Movie Distributor" "Transaction subject"
                Expenses:Movies   30.00 EUR
                Assets:Paypal    -30.00 EUR

            2020-12-11 balance Assets:Paypal                                   -30.00 EUR
        """,
        )


if __name__ == "__main__":
    unittest.main()
