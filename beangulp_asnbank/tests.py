from beangulp_asnbank import importer

from beancount.parser import cmptest, printer, parser
from beancount.utils.test_utils import docfile
from beangulp import extract
import itertools

accounts = {
    "IBAN_CHEQUING": "Assets:Chequing",
    "IBAN_SAVINGS": "Assets:Spaarrekening",
    "IBAN_INVESTING": "Assets:Beleggen",
}

DUPLICATE = extract.DUPLICATE


class StringOutput:
    def __init__(self) -> None:
        self.s = ""

    def write(self, s: str):
        self.s = self.s + s

    def get(self) -> str:
        self.s


class TestAsnBank(cmptest.TestCase):
    @docfile
    def test_topup_transaction(self, filename: str) -> None:
        """\
14-10-2021,IBAN_CHEQUING,IBAN_PAYEE,payee,,,,EUR,150.00,EUR,-10.00,14-10-2021,14-10-2021,0000,INC,00000000,,'Narration of transaction',0
        """
        asnbank_importer = importer.Importer(accounts)
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
05-10-2021,IBAN_SAVINGS,,,,,,EUR,100.00,EUR,1.00,05-10-2021,01-10-2021,0000,RNT,00000000,,'CREDITRENTE                     TOT 01-10-21',0
        """
        asnbank_importer = importer.Importer(accounts, interest_account="Income:Rente")
        entries = asnbank_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2021-10-05 balance Assets:Spaarrekening                            100.00 EUR

2021-10-05 * "CREDITRENTE                     TOT 01-10-21"
  Assets:Spaarrekening   1.00 EUR
  Income:Rente          -1.00 EUR


""",
        )

    @docfile
    def test_investment_buy(self, filename: str) -> None:
        """\
04-10-2021,IBAN_INVESTING,,,,,,EUR,12.50,EUR,-12.50,04-10-2021,06-10-2021,0000,EFF,00000000,,'Voor u gekocht via Euronext Fund Services: 0 1000 Participaties ASN Duurzaam Mixfonds Neutraal a EUR 50 00. Valutadatum:       06/10/2021. Positie na          transactie: 0 1100 ASN Duurzaam Mixfonds Offensief. (Trans.nr. 00000000)',0
        """
        asnbank_importer = importer.Importer(
            accounts,
            investment_account="Assets:Beleggen:Fonds",
            profit_loss_account="Income:PL",
        )
        entries = asnbank_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s
        expected = """\
;; -*- mode: beancount -*-

**** filepath

2021-10-04 balance Assets:Beleggen                                 12.50 EUR

2021-10-04 * "Aankoop beleggen"
  Assets:Beleggen                                 -12.50 EUR
  Assets:Beleggen:Fonds:DuurzaamMixfondsNeutraal  0.1000 ASN_MIXFONDS_NEUTRAAL {50.00 EUR}


"""

        self.assertEqual(actual, expected)

    @docfile
    def test_investment_sell(self, filename: str) -> None:
        """\
04-11-2021,IBAN_INVESTING,,,,,,EUR,100.00,EUR,120.00,04-11-2021,08-11-2021,0000,EFF,00000010,,'Voor u verkocht via Euronext    Fund Services: 0 1000          Participaties ASN               Microkredietfonds a EUR 50 00.  Valutadatum: 08/11/2021. Positie na transactie: 0 0000 ASN    Microkredietfonds. (Trans.nr.   0000000000)',0
        """
        asnbank_importer = importer.Importer(
            accounts,
            investment_account="Assets:Beleggen:Fonds",
            profit_loss_account="Income:PL",
        )
        entries = asnbank_importer.extract(filename, [])
        output = StringOutput()
        extract.print_extracted_entries([["filepath", entries]], output)
        actual = output.s

        self.assertEqual(
            actual,
            """\
;; -*- mode: beancount -*-

**** filepath

2021-11-04 balance Assets:Beleggen                                 100.00 EUR

2021-11-04 * "Verkoop beleggen"
  Assets:Beleggen                           120.00 EUR
  Assets:Beleggen:Fonds:Microkredietfonds  -0.1000 ASN_MICROKREDIETFONDS {} @ 50.00 EUR
  Income:PL


""",
        )

    @docfile
    def test_duplicate_filtering(self, filename: str) -> None:
        """\
09-01-2022,IBAN_CHEQUING,IBAN_SAVINGS,name,,,,EUR,50.21,EUR,10.00,09-01-2022,09-01-2022,1234,IOB,12345678,,GEEN,1
        """

        # 09-01-2022,IBAN_MAIN,IBAN_OTHER,rekeningtype,,,,EUR,10.00,EUR,-10.00,09-01-2022,09-01-2022,0000,IOB,00000000,,GEEN,0
        existing_entries = parser.parse_many(
            """\
2022-01-09 * "name" "GEEN"
  Assets:Spaarrekening  -10.00 EUR
  Assets:Chequing        10.00 EUR

        """
        )
        asnbank_importer = importer.Importer(
            accounts,
            investment_account="Assets:Beleggen:Fonds",
            profit_loss_account="Income:PL",
        )
        entries = asnbank_importer.extract(filename, existing_entries)
        entries = asnbank_importer.deduplicate(entries, existing_entries)

        assert entries[1].meta[DUPLICATE] == True
