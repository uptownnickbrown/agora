from app.engine.orderbook import BUY, SELL, Order, OrderBook


def make(book, oid, agent, side, qty, price, tick=0, ttl=100):
    return book.submit(
        Order(order_id=oid, agent_id=agent, good="grain", side=side,
              qty=qty, price=price, placed_tick=tick, expires_tick=tick + ttl),
        tick,
    )


def test_limit_orders_rest_until_crossed():
    book = OrderBook("grain")
    assert make(book, 1, "a", SELL, 5, 100) == []
    assert book.best_ask() == 100
    trades = make(book, 2, "b", BUY, 3, 100)
    assert len(trades) == 1
    assert (trades[0].price, trades[0].qty) == (100, 3)
    assert book.depth(SELL) == 2


def test_price_time_priority_and_resting_price_execution():
    book = OrderBook("grain")
    make(book, 1, "a", SELL, 1, 105)
    make(book, 2, "b", SELL, 1, 100)  # better price, later time
    make(book, 3, "c", SELL, 1, 100)  # same price, even later
    trades = make(book, 4, "d", BUY, 3, 200)
    assert [t.price for t in trades] == [100, 100, 105]  # best price first
    assert [t.seller_id for t in trades] == ["b", "c", "a"]  # then time priority


def test_partial_fill_rests_remainder():
    book = OrderBook("grain")
    make(book, 1, "a", SELL, 2, 90)
    trades = make(book, 2, "b", BUY, 5, 95)
    assert sum(t.qty for t in trades) == 2
    assert book.best_bid() == 95
    assert book.depth(BUY) == 3


def test_market_order_never_rests():
    book = OrderBook("grain")
    make(book, 1, "a", SELL, 2, 90)
    trades = book.submit(
        Order(order_id=2, agent_id="b", good="grain", side=BUY, qty=10,
              price=None, placed_tick=0),
        0,
    )
    assert sum(t.qty for t in trades) == 2
    assert book.best_bid() is None  # unfilled market remainder is discarded


def test_no_self_trade():
    book = OrderBook("grain")
    make(book, 1, "a", SELL, 1, 90)
    make(book, 2, "z", SELL, 1, 95)
    trades = make(book, 3, "a", BUY, 1, 200)
    assert len(trades) == 1
    assert trades[0].seller_id == "z"  # skipped own ask, matched the worse price
    assert book.best_ask() == 90       # own order returned to the book


def test_expiry_reports_unfilled_quantity():
    book = OrderBook("grain")
    make(book, 1, "a", BUY, 7, 50, tick=0, ttl=2)
    expired = book.expire(5)
    assert [(o.order_id, qty) for o, qty in expired] == [(1, 7)]
    assert book.best_bid() is None


def test_cancel():
    book = OrderBook("grain")
    make(book, 1, "a", SELL, 5, 100)
    assert book.cancel(1) is True
    assert book.cancel(1) is False
    assert book.best_ask() is None
