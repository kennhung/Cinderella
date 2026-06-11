import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from beancount.core.amount import Amount

from cinderella.datatypes import Transactions, StatementType
from cinderella.parsers.base import StatementParser


class Next(StatementParser):
    identifier = "next"

    def __init__(self):
        super().__init__()
        self.default_source_accounts = {
            StatementType.creditcard: "Liabilities:Debit:Next",
            StatementType.bank: "Assets:Bank:TW:NEXT:Main",
        }

    def _read_statement(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, encoding="utf8", skiprows=0, thousands=",")
        return df

    def _parse_card_statement(self, records: pd.DataFrame) -> Transactions:
        raise NotImplementedError()

    def _parse_bank_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.bank
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            date = datetime.strptime(record["交易日期"], "%Y/%m/%d")
            title = record["摘要"]

            if title == "儲值付款":
                continue

            if (type(record["收入"]) == int or type(record["收入"]) == float) and record["收入"] != 0:
                price = Decimal(record["收入"])
            elif (type(record["支出"]) == int or type(record["支出"]) == float) and record["支出"] != 0:
                price = Decimal(-record["支出"])
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                )

            currency = "TWD"
            account = self.default_source_accounts[category]

            posting = self.beancount_api.make_simple_posting(account, price, currency)
            transaction = self.beancount_api.make_transaction(
                date, title, [posting], meta={"c_source": "bank.next"})

            comment = ""
            if not pd.isna(record["備註"]):
                comment += str(record["備註"])

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions
