import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
import logging

from cinderella.datatypes import Transactions, StatementType
from cinderella.parsers.base import StatementParser

# Turn off logs from pdfminer used by camelot
logging.getLogger("pdfminer").setLevel(logging.ERROR)


class CTBC(StatementParser):
    identifier = "ctbc"

    # FIXME: Fix problem of wrong currency mapping
    country_currency_map = {
        "US": "USD",
        "AU": "AUD",
        "NL": "USD"
    }

    def __init__(self):
        super().__init__()
        self.default_source_accounts = {
            StatementType.creditcard: "Liabilities:Debit:CTBC",
            StatementType.bank: "Assets:Bank:TW:CTBC",
        }

    def _read_statement(self, filepath: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(filepath, encoding="utf8", skiprows=2, thousands=",")
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="big5", skiprows=2, thousands=",")
        return df

    def _parse_card_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.creditcard
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            date = datetime.strptime(record["交易日"], "%Y/%m/%d")
            posting_date = datetime.strptime(record["入帳日"], "%Y/%m/%d")
            title = record["摘要"]
            if type(title) != 'string' or len(title) == 0:
                title = "VISA 簽帳卡消費"

            if not np.isnan(record["支出"]):
                price = -Decimal(record["支出"])
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                )

            currency = "TWD"
            account = self.default_source_accounts[category]

            country = record["消費地"]
            if country != "TW" and record["支出"] != record["消費地金額"]:
                foreign_price = record["消費地金額"]

                if country not in self.country_currency_map:
                    raise RuntimeError(
                        f"Can not parse {self.identifier} {category.name} statement {record}"
                    )

                amount = self.beancount_api.make_amount(-price, currency)
                posting = self.beancount_api.make_posting(account, amount, meta={"foreign_currency": self.country_currency_map[country], "foreign_price": foreign_price})
            else:
                posting = self.beancount_api.make_simple_posting(account, -price, currency)

            transaction = self.beancount_api.make_transaction(date, title, [posting], meta={"post_date": posting_date})

            comment = ""
            if country != "TW" and record["支出"] != record["消費地金額"]:
                comment += f"{country} / {record["消費地金額"]} / {record["外幣折算日"]}"

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions

    def _parse_bank_statement(self, records: pd.DataFrame) -> Transactions:
        category = StatementType.bank
        transactions = Transactions(category, self.identifier)

        for _, record in records.iterrows():
            date = datetime.strptime(record["日期"], "%Y/%m/%d")
            title = record["摘要"]
            if not np.isnan(record["支出"]):  # spend
                price = -Decimal(record["支出"])
            elif not np.isnan(record["存入"]):  # income
                price = Decimal(record["存入"])
            else:
                raise RuntimeError(
                    f"Can not parse {self.identifier} {category.name} statement {record}"
                )

            currency = "TWD"
            account = self.default_source_accounts[category]

            posting = self.beancount_api.make_simple_posting(account, price, currency)
            transaction = self.beancount_api.make_transaction(date, title, [posting], meta={"c_source": "bank.ctbc"})

            comment = ""
            if not pd.isna(record["備註"]):
                comment += str(record["備註"])
            if not pd.isna(record["轉出入帳號"]):
                comment += str(record["轉出入帳號"])
            if not pd.isna(record["註記"]):
                comment += str(record["註記"])

            if comment:
                self.beancount_api.add_transaction_comment(transaction, comment)

            transactions.append(transaction)

        return transactions
