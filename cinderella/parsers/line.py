import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from beancount.core.amount import Amount

from cinderella.datatypes import Transactions, StatementType
from cinderella.parsers.base import StatementParser

class LineMain(StatementParser):
    identifier = "line"

    def __init__(self):
        super().__init__()
        self.default_source_accounts = {
            StatementType.creditcard: "Liabilities:Debit:Line",
            StatementType.bank: "Assets:Bank:TW:LINE:Main",
        }
    
    def _read_statement(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, encoding="utf8", skiprows=0, thousands=",")
        return df

    def _parse_card_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.creditcard
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            dates = record["消費日/入帳日"].split(" /")
            date = datetime.strptime(dates[0], "%Y.%m.%d")
            title = record["交易說明"]

            if pd.notna(record["新臺幣金額"]):
                    price_str = record["新臺幣金額"].replace(",", "").replace("$", "")
                    price = Decimal(price_str)
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                ) 

            currency = "TWD"
            account = self.default_source_accounts[category]

            if record["消費國家"] != "TW":
                foreign_info = record["外幣消費金額/換匯日"].split("/")
                foreign_dollar = foreign_info[0].split(" ")

                amount = self.beancount_api.make_amount(-price, currency)
                posting = self.beancount_api.make_posting(account, amount, meta={"foreign_currency": foreign_dollar[0], "foreign_price": foreign_dollar[1]})
            else:
                posting = self.beancount_api.make_simple_posting(account, -price, currency)
            
            transaction = self.beancount_api.make_transaction(date, title, [posting], meta={"c_source": "card.line"})

            comment = ""
            if not pd.isna(record["外幣消費金額/換匯日"]) and record["外幣消費金額/換匯日"] != "-":
                comment += str(record["外幣消費金額/換匯日"])

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions

    def _parse_bank_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.bank
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            date = datetime.strptime(record["日期"], "%Y.%m.%d")
            title = record["交易說明"]
            if pd.notna(record["交易金額"]):
                if type(record["交易金額"]) == int or type(record["交易金額"]) == float:
                    price = Decimal(record["交易金額"])
                else:
                    price_str = record["交易金額"].replace(",", "").replace("$", "")
                    price = Decimal(price_str)
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                )

            currency = "TWD"
            account = self.default_source_accounts[category]

            posting = self.beancount_api.make_simple_posting(account, price, currency)
            transaction = self.beancount_api.make_transaction(date, title, [posting], meta={"c_source": "bank.line"})

            comment = ""
            if not pd.isna(record["備註"]):
                comment += str(record["備註"])

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions
