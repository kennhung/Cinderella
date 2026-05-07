import pandas as pd
from datetime import datetime
from decimal import Decimal

from cinderella.datatypes import Transactions, StatementType
from cinderella.parsers.base import StatementParser


class EasyCard(StatementParser):
    identifier = "easycard"

    def __init__(self):
        super().__init__()
        self.default_source_accounts = {
            StatementType.bank: "Assets:EasyCard:NYCU",
        }

    def _read_statement(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, encoding="utf8", skiprows=0, thousands=",")
        return df

    def _parse_card_statement(self, records: pd.DataFrame) -> Transactions:
        raise NotImplementedError

    def _parse_bank_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.bank
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            date = datetime.strptime(record["交易時間"], "%Y-%m-%d %H:%M:%S")

            if record["交易類別"] == "加值":
                title = "NYCU 悠遊卡加值"
                payee = None
            else:
                title = record['交易場所']
                payee = record["服務業者"]

            if pd.notna(record["交易金額"]):
                if record["交易類別"] == "加值":
                    price = Decimal(record["交易金額"])
                else:
                    price = Decimal(record["交易金額"]) * -1
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                )

            currency = "TWD"
            account = self.default_source_accounts[category]

            posting = self.beancount_api.make_simple_posting(account, price, currency)
            transaction = self.beancount_api.make_transaction(
                date, title, [posting], payee=payee, meta={"c_source": "bank.easycard"})

            comment = ""
            if not pd.isna(record["服務業者"]):
                comment += str(record["服務業者"])

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions
