from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only
from datetime import datetime
import sys

from models import Base, Order, Log

engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)


@app.before_request
def create_session():
    g.session = scoped_session(DBSession)


@app.teardown_appcontext
def shutdown_session(response_or_exc):
    sys.stdout.flush()
    g.session.commit()
    g.session.remove()


""" Suggested helper methods """


def check_sig(payload, sig):
    if payload['platform'] == 'Ethereum':
        eth_encoded_message = eth_account.messages.encode_defunct(text=payload)
        return eth_account.Account.recover_message(eth_encoded_message, signature=sig) == payload['sender_pk']
    else:
        return  algosdk.util.verify_bytes(payload.encode('utf-8'), sig, payload['sender_pk'])
    
    
def fill_order(order): # process_order from order_book.py to replace fill_order
    session = g.session
    # just use order as new_order in order_book.py. It matters!

    # add order to sessions
    session.add(order)
    session.commit()

    # check if there are any existing order that matches
    while (order is not None):
        for existing_order in session.query(Order).filter(Order.filled == None).all():
            # if a good rate found,set to filled
            if existing_order.filled == None and existing_order.buy_currency == order.sell_currency and \
                    existing_order.sell_currency == order.buy_currency and \
                    existing_order.sell_amount / existing_order.buy_amount >= order.buy_amount / order.sell_amount:

                order.filled = datetime.now()
                existing_order.filled = datetime.now()
                existing_order.counterparty_id = order.id
                order.counterparty_id = existing_order.id

                if order.buy_amount < existing_order.sell_amount:
                    remaining_sell = existing_order.sell_amount - order.buy_amount
                    remaining_buy =  remaining_sell/(existing_order.sell_amount / existing_order.buy_amount)
                    order = Order(sender_pk=existing_order.sender_pk, receiver_pk=existing_order.receiver_pk,
                                      buy_currency=existing_order.buy_currency,
                                      sell_currency=existing_order.sell_currency, buy_amount=remaining_buy,
                                      sell_amount=remaining_sell, creator_id=existing_order.id, filled=None)
                    session.add(order)
                    session.commit()
                elif order.buy_amount>existing_order.sell_amount :
                    remaining_buy = order.buy_amount - existing_order.sell_amount
                    remaining_sell = remaining_buy/(order.buy_amount/ order.sell_amount)
                    order = Order(sender_pk=order.sender_pk,receiver_pk=order.receiver_pk,
                                        buy_currency=order.buy_currency, sell_currency=order.sell_currency,
                                        sell_amount= remaining_sell, buy_amount=remaining_buy, creator_id=order.id, filled=None)
                    session.add(order)
                    session.commit()

                else:
                    # exact amount,no child
                    order = None
                break
        return


def log_message(d):
    # Takes input dictionary d and writes it to the Log table
    # Hint: use json.dumps or str() to get it in a nice string form
    g.session.add(Log(logtime = datetime.now(), message = json.dumps(d)))
    g.session.commit()

    
""" End of helper methods """


@app.route('/trade', methods=['POST'])
def trade():
    print("In trade endpoint")
    if request.method == "POST":
        content = request.get_json(silent=True)
        print(f"content = {json.dumps(content)}")
        columns = ["sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform"]
        fields = ["sig", "payload"]

        for field in fields:
            if not field in content.keys():
                print(f"{field} not received by Trade")
                print(json.dumps(content))
                log_message(content)
                return jsonify(False)

        for column in columns:
            if not column in content['payload'].keys():
                print(f"{column} not received by Trade")
                print(json.dumps(content))
                log_message(content)
                return jsonify(False)

        # Your code here
        # Note that you can access the database session using g.session
        
        sig = content['sig']
        payload = json.dumps(content['payload'])
        sender_pk = content['payload']['sender_pk']
        receiver_pk = content['payload']['receiver_pk']
        buy_currency = content['payload']['buy_currency']
        sell_currency = content['payload']['sell_currency']
        buy_amount = content['payload']['buy_amount']
        sell_amount = content['payload']['sell_amount']
        platform = content['payload']['platform']

        # TODO: Check the signature
        # TODO: Add the order to the database
        # TODO: Fill the order
        # TODO: Be sure to return jsonify(True) or jsonify(False) depending on if the method was successful
        if platform == 'Ethereum':
            eth_encoded_message = eth_account.messages.encode_defunct(text=payload)
            if eth_account.Account.recover_message(eth_encoded_message, signature=sig) == sender_pk:
                fill_order(Order(sender_pk=sender_pk, receiver_pk=receiver_pk, buy_currency=buy_currency,sell_currency=sell_currency, buy_amount=buy_amount, sell_amount=sell_amount,
                                    signature=sig))
                return jsonify(True)
            else:
                log_message(content)
                return jsonify(False)
        elif platform == 'Algorand':
            if algosdk.util.verify_bytes(payload.encode('utf-8'), sig, sender_pk):
                fill_order(Order(sender_pk=sender_pk, receiver_pk=receiver_pk, buy_currency=buy_currency,sell_currency=sell_currency, buy_amount=buy_amount, sell_amount=sell_amount,
                                    signature=sig))
                return jsonify(True)
            else:
                log_message(content)
                return jsonify(False)

@app.route('/order_book')
def order_book(): # order_book from database_endpoint.py
    # Your code here
    # Note that you can access the database session using g.session
    orders = g.session.query(Order).filter().all()
    newList = []

    for i in orders:
        order = {}
        order['sender_pk'] = i.sender_pk
        order['receiver_pk'] = i.receiver_pk
        order['buy_currency'] = i.buy_currency
        order['sell_currency'] = i.sell_currency
        order['buy_amount'] = i.buy_amount
        order['sell_amount'] = i.sell_amount
        order['signature'] = i.signature
        newList.append(order)

    result = {}
    result['data'] = newList
    return jsonify(result)


if __name__ == '__main__':
    app.run(port='5002')