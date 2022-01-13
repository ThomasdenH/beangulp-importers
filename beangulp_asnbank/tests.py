from beangulp_asnbank import importer

from beancount.parser import cmptest, printer
from beancount.utils.test_utils import docfile


class TestOvchipkaart(cmptest.TestCase):
    @docfile
    def test_topup_transaction(self, filename: str) -> None:
        """\
14-10-2021,OWN_IBAN,IBAN_PAYEE,payee,,,,EUR,150.00,EUR,-10.00,14-10-2021,14-10-2021,0000,INC,00000000,,'Narration of transaction',0
        """
        asnbank_importer = importer.Importer("Assets:Chequing")
        entries = asnbank_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """       
            2021-10-14 balance Assets:Chequing                                 150.00 EUR

            2021-10-14 * "payee" "Narration of transaction"
                Assets:Chequing  -10.00 EUR
        """,
        )

    @docfile
    def test_interest_posting(self, filename: str) -> None:
        """\
05-10-2021,OWN_IBAN,,,,,,EUR,100.00,EUR,1.00,05-10-2021,01-10-2021,0000,RNT,00000000,,'CREDITRENTE                     TOT 01-10-21',0
        """
        asnbank_importer = importer.Importer(
            "Assets:Spaarrekening", interest_account="Income:Rente"
        )
        entries = asnbank_importer.extract(filename, [])
        # For some reason comparing directly doesn't work
        actual = ""
        for entry in entries:
            actual = actual + printer.format_entry(entry)

        expected = """\
2021-10-05 balance Assets:Spaarrekening                            100.00 EUR
2021-10-05 * "CREDITRENTE                     TOT 01-10-21"
  Assets:Spaarrekening   1.00 EUR
  Income:Rente          -1.00 EUR
"""

        self.assertEqual(actual, expected)

    @docfile
    def test_investment_buy(self, filename: str) -> None:
        """\
04-10-2021,OWN_IBAN,,,,,,EUR,12.50,EUR,-12.50,04-10-2021,06-10-2021,0000,EFF,00000000,,'Voor u gekocht via Euronext Fund Services: 0 1000 Participaties ASN Duurzaam Mixfonds Neutraal a EUR 50 00. Valutadatum:       06/10/2021. Positie na          transactie: 0 1100 ASN Duurzaam Mixfonds Offensief. (Trans.nr. 00000000)',0
        """
        asnbank_importer = importer.Importer(
            "Assets:Beleggen",
            investment_account="Assets:Beleggen:Fonds",
            profit_loss_account="Income:PL",
        )
        entries = asnbank_importer.extract(filename, [])
        # For some reason comparing directly doesn't work
        actual = ""
        for entry in entries:
            actual = actual + printer.format_entry(entry)

        expected = """\
2021-10-04 balance Assets:Beleggen                                 12.50 EUR
2021-10-04 * "Aankoop beleggen"
  Assets:Beleggen                                 -12.50 EUR
  Assets:Beleggen:Fonds:DuurzaamMixfondsNeutraal  0.1000 ASN_MIXFONDS_NEUTRAAL {50.00 EUR}
"""

        self.assertEqual(actual, expected)

    @docfile
    def test_investment_sell(self, filename: str) -> None:
        """\
04-11-2021,OWN_IBAN,,,,,,EUR,100.00,EUR,120.00,04-11-2021,08-11-2021,0000,EFF,00000010,,'Voor u verkocht via Euronext    Fund Services: 0 1000          Participaties ASN               Microkredietfonds a EUR 50 00.  Valutadatum: 08/11/2021. Positie na transactie: 0 0000 ASN    Microkredietfonds. (Trans.nr.   0000000000)',0
        """
        asnbank_importer = importer.Importer(
            "Assets:Beleggen",
            investment_account="Assets:Beleggen:Fonds",
            profit_loss_account="Income:PL",
        )
        entries = asnbank_importer.extract(filename, [])
        # For some reason comparing directly doesn't work
        actual = ""
        for entry in entries:
            actual = actual + printer.format_entry(entry)

        expected = """\
2021-11-04 balance Assets:Beleggen                                 100.00 EUR
2021-11-04 * "Verkoop beleggen"
  Assets:Beleggen                           120.00 EUR
  Assets:Beleggen:Fonds:Microkredietfonds  -0.1000 ASN_MICROKREDIETFONDS {} @ 50.00 EUR
  Income:PL
"""

        self.assertEqual(actual, expected)
