import pandas as pd

from cinderella.datatypes import Transactions, StatementType
from cinderella.parsers.line import LineMain

class LinePocket(LineMain):
    

    def __init__(self):
        super().__init__()
        self.identifier = "lip"
        self.default_source_accounts = {
            StatementType.bank: "Assets:Bank:TW:LINE:Pocket",
        }

    def _parse_card_statement(self, records: pd.DataFrame) -> Transactions:
        raise NotImplementedError("Line Pocket does not support credit card statements")