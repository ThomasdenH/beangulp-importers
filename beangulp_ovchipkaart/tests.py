from beangulp_ovchipkaart import importer

from beancount.parser import cmptest
from beancount.utils.test_utils import docfile


class TestPaypal(cmptest.TestCase):
    @docfile
    def test_topup_transaction(self, filename: str) -> None:
        """\
"Datum";"Check-in";"Vertrek";"Check-uit";"Bestemming";"Bedrag";"Transactie";"Klasse";"Product";"Opmerkingen";"Naam";"Kaartnummer"
"29-03-2021";"16:00";"";"";"bij NS";"10,00";"Saldo automatisch opgeladen";"";"";"";"Card owner name";"1234 5678 9012 3456"
        """
        ovchipkaart_importer = importer.Importer(
            "Assets:Vervoer:OvChipkaarttegoed", "Liabilities:OvIncasso", "EUR"
        )
        entries = ovchipkaart_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """        
            2021-03-29 * "Saldo automatisch opgeladen bij NS"
                Assets:Vervoer:OvChipkaarttegoed     10.00 EUR
                Liabilities:OvIncasso               -10.00 EUR
        """,
        )

    @docfile
    def test_travel_transaction(self, filename: str) -> None:
        """\
"Datum";"Check-in";"Vertrek";"Check-uit";"Bestemming";"Bedrag";"Transactie";"Klasse";"Product";"Opmerkingen";"Naam";"Kaartnummer"
"29-03-2021";"";"Eindhoven Centraal";"11:49";"Nijmegen";"8,88";"Check-uit";"";"Transactiebeschrijving";"";"Card owner name";"1234 5678 9012 3456"
        """
        ovchipkaart_importer = importer.Importer(
            "Assets:Vervoer:OvChipkaarttegoed", "Liabilities:OvIncasso", "EUR"
        )
        entries = ovchipkaart_importer.extract(filename, [])
        self.assertEqualEntries(
            entries,
            """
            2021-03-29 * "Eindhoven Centraal - Nijmegen - Transactiebeschrijving"
                Assets:Vervoer:OvChipkaarttegoed  -8.88 EUR
        """,
        )
