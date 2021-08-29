from datetime import datetime
from decimal import Decimal

from datatypes import Operation, Directive, Directives, Item
from .base import StatementParser


class Taishin(StatementParser):
    name = "taishin"
    def __init__(self, config: dict = {}):
        super().__init__()
        self.default_source_accounts = {
            "card": "Liabilities:CreditCard:Taishin",
            "bank": "Assets:Bank:Taishin",
        }

    def _parse_card_statement(self, records: list) -> Directives:
        directives = Directives("card", self.name)
        for record in records:
            date = datetime.strptime(record[0], '%Y/%m/%d')
            item = record[4]
            amount, currency = self._parse_price(record[3])
            # statement use negative number as expense, turn to positive in our structure
            amount *= Decimal(-1.0)

            directive = Directive(date, item, amount, currency)
            directive.operations.append(
                Operation(self.default_source_accounts["card"], -amount, currency)
            )
            directives.append(directive)

        return directives

    def _parse_bank_statement(self, records: list) -> Directives:
        directives = Directives("bank", self.name)
        for record in records:
            date = datetime.strptime(record[0], '%Y/%m/%d')
            item = record[6]
            amount, currency = self._parse_price(record[3])
            directive = Directive(date, item, amount, currency)
            directive.operations.append(
                Operation(self.default_source_accounts["bank"], amount, currency)
            )
            directive.items.append(Item(record[4], amount))

            directives.append(directive)

        return directives

    def _parse_price(self, raw_str: str) -> tuple:
        premise, amount_str = raw_str.split("$", maxsplit=1)
        amount = Decimal(amount_str.replace(",", ""))

        # used as expense, convert to positive
        if premise.startswith("-"):
            amount *= -1

        return (amount, "TWD")
