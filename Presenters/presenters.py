import sys
from pathlib import Path
from collections import namedtuple

PARENT_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_PATH))

import models.oanda_api as OandaAPI
from models.news_api import latest_news
from models.database_connections import PRMS_Database
from models.vantage_alpha_api import AV_FXData
from models.algo_trading_api import Algo
from models.calculations import Convertprice


class LoginPage(object):
    def __init__(self, view):
        super().__init__()
        self.View = view

    def validate_login(self, username, password):
        with PRMS_Database() as db:
            validation = db.Validate_login(username, password)
        return validation


class RegistrationPage(object):
    def __init__(self, view):
        super().__init__()
        self.View = view

    def validate_registration(self, username, password):
        with PRMS_Database() as db:
            validation = db.registration(username, password)
        return validation


class HomePage(object):

    def __init__(self, view):
        super().__init__()
        self.View = view

    def create_pie_data(self):
        try:
            with PRMS_Database() as db:
                df = db.get_largest_positions()
                names = df["name"]
        except TypeError:
            return None  # positions are empty

        market_vals = abs(df["MarketVal"])
        data = {"market_values": market_vals, "names": names}
        self.View.draw_pie_chart(data=data)

    def create_tables(self):
        Tables = namedtuple("Tables", ("account", "prices", "news"))
        account = OandaAPI.oanda_acc_summary()
        price_rows = OandaAPI.oanda_prices()
        news_rows = latest_news()
        T = Tables(account, price_rows, news_rows)
        self.View.update_tables(Tables=T)

    def create_rec_summary(self):
        rec = OandaAPI.Reconciliation()
        info = rec.num_matches()
        self.View.update_rec_summary(text=info)


class CreateOrders(object):

    def __init__(self, view):
        self.View = view

    def create_positions(self):
        positions = OandaAPI.live_positions("basic")
        self.View.update_positions(rows=positions)

    def execute_trade(self, units, instrument, acknowledged=False):
        if not acknowledged:
            info = ("The trade is not acknowledged.\n"
                    "Your order has not been sent.")
        else:
            order_details = OandaAPI.market_order(units, instrument)
            OandaAPI.trade_to_db(order_details)
            info = OandaAPI.execution_details(order_details)

        self.View.clear_entries()
        self.View.display_order_info(text=info)
        self.View.refresh_positions()


class AlgoTrading(object):
    def __init__(self, view):
        self.View = view
        self.counter = 0

    def create_algo_chart(self, currency1, currency2, strategy):
        Chart = Algo(currency1, currency2)
        Chart_data = Chart.live_algo_chart(strategy)
        self.View.draw_algo_chart(data=Chart_data, strategy=strategy)

    # PAUSED to be reviewed
    # def run_algorithm(self, timer, units, currency1, currency2, strategy):
    #     while timer > self.counter:
    #         print(f"order initiated, {self.counter} interval elapsed")
    #         root.after(120000,
    #                    self.Algorithm_orders(units, currency1, currency2, strategy))  # 120k millsecs = 2mins # i think instead of root its controller
    #         self.counter += 2
    #     self.counter = 0
    #     print("Time period elapsed")
    #
    # def Algorithm_orders(self): # executing trades
    #     units = self.entry_units.get()
    #     ccy1 = self.entry_ccy1.get()
    #     ccy2 = self.entry_ccy2.get()
    #     algo_strategy = self.strategy.get()
    #     self.label_fil["text"] = Algo(ccy1, ccy2).algo_execution(units, algo_strategy)


class SecurityPrices(object):

    def __init__(self, view):
        self.View = view

    def create_chart(self, period, indicator, currency1, currency2):
        Chart = AV_FXData(period, currency1, currency2, indicator)
        Chart_data = Chart.fx_chart_gui()

        Chart_prices = Chart_data.tail(4)  # gets the 4 most recent prices
        Chart_prices = Chart_prices[["Date", "Close Price"]]
        prices = Chart_prices.to_numpy().tolist()

        self.View.draw_chart(data=Chart_data, indicator=indicator)
        self.View.clear_prices()
        self.View.display_prices(rows=prices)


class CurrentPositions(object):

    def __init__(self, view):
        self.View = view

    def create_positions(self):
        positions = OandaAPI.live_positions("advanced")
        self.View.update_positions(rows=positions)


class PositionReconciliation(object):

    def __init__(self, view):
        self.View = view

    def create_rec(self):
        self.View.clear_table()
        rec = OandaAPI.Reconciliation()
        rec_table = rec.generate_rec()
        rec_table_rows = rec_table.to_numpy().tolist()
        self.View.update_table(rows=rec_table_rows)


class TradeBookings(object):
    def __init__(self, view):
        self.View = view

    def get_transactions(self):
        with PRMS_Database() as db:
            positions = db.get_all_positions()
        entries = positions.to_numpy().tolist()
        self.View.display_transactions(rows=entries)

    def store_transaction(self, name, quantity, price):
        with PRMS_Database() as db:
            check = db.validate_entry(name, quantity, price)
            if isinstance(check, str):  # if validation Failed
                print(check)
                return None
            else:
                print(db.add_to_db(name, quantity, price))
                self.View.clear_status_entries()

    def set_transaction_status(self, id, toggle):
        with PRMS_Database() as db:
            print(db.cancelled_toggle(id, toggle))
            self.View.clear_status_entries()


class UsTreasuryConvWindow(object):
    def __init__(self, view):
        self.View = view

    def conversion(self, price):
        converted_price = Convertprice(price)
        self.View.display_conversion(new_price=converted_price)
