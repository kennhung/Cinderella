from decimal import Decimal
from beancount.core.data import Amount

from cinderella.beanlayer import BeanCountAPI
from cinderella.datatypes import Transactions
from cinderella.settings import CinderellaSettings


class AccountClassifier:
    def __init__(self, settings: CinderellaSettings):
        self.settings = settings
        self.beancount_api = BeanCountAPI()
        # setup default accounts
        default_account = settings.default_accounts
        self.default_expense_account = default_account.get("expenses", "Expenses:Other")
        self.default_income_account = default_account.get("income", "Income:Other")

        # load mappings
        self.general_map = self.settings.get_mapping("general")

    def classify_account(self, transactions: Transactions) -> None:
        specific_map = self.settings.get_mapping(transactions.source)
        pattern_maps = [specific_map, self.general_map]  # former has higher priority

        for transaction in transactions:
            if len(transaction.postings) >= 2:
                continue
            account = self._match_patterns(
                transaction, pattern_maps, self.default_expense_account
            )
            amount = transaction.postings[0].units

            if "foreign_currency" in transaction.postings[0].meta:
                foreign_currency = transaction.postings[0].meta["foreign_currency"]
                foreign_price = Decimal(transaction.postings[0].meta["foreign_price"])

                transaction.postings[0].meta.pop("foreign_currency")
                transaction.postings[0].meta.pop("foreign_price")

                ntd_price = transaction.postings[0].units.number
                bean_price = Amount(abs((ntd_price / foreign_price).quantize(Decimal(".00000001"))), "TWD")

                amount = self.beancount_api.make_amount(Decimal(foreign_price), foreign_currency)
                posting = self.beancount_api.make_posting(account, amount, price=bean_price)
                transaction.postings.append(posting)
                continue

            self.beancount_api.create_and_add_transaction_posting(
                transaction, account, -amount.number, amount.currency
            )

    def _match_patterns(
        self, transaction, pattern_maps: list, default_account: str
    ) -> str:
        for pattern_map in pattern_maps:
            for account, keywords in pattern_map.items():
                found = self.beancount_api.find_keywords(transaction, keywords)
                if found:
                    return account
        return default_account
