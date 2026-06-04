import base64
from flask import Flask, render_template, request, jsonify
from serial_wallet import send_to_esp32
from solana_utils import create_tx, build_signed_tx
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.signature import Signature
import requests

app = Flask(__name__)
client = Client("https://api.devnet.solana.com")

WALLET_ADDRESS = "oggYcXGKBcEWB25SiRfBd6iCHE6dB6xkB2bzgfkxdTc"
# ESP32_WALLET ="<put-your-generated-wallets-publicKey-here>"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send_transaction():
    try:
        recipient = request.form["recipient"]
        amount = float(request.form["amount"])

        tx_data = create_tx(recipient=recipient, amount_sol=amount)

        message_bytes = base64.b64decode(tx_data["message_bytes"])
        esp32_response = send_to_esp32(message_bytes)

        if not esp32_response.get("success"):
            return jsonify({
                "success": False,
                "error": esp32_response.get("error", "ESP32 signing failed"),
                "tag_uid": esp32_response.get("tag_uid")
            })

        signed_tx = build_signed_tx(
            message_bytes_b64=tx_data["message_bytes"],
            signature_b58=esp32_response["signature"],
            msg_object=tx_data["msg_object"],
        )

        tx_sig = client.send_raw_transaction(signed_tx).value

        return jsonify({
            "success": True,
            "tx_signature": str(tx_sig),
            "explorer": f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/balance")
def balance():
    try:
        pubkey = Pubkey.from_string(WALLET_ADDRESS)

        resp = client.get_balance(pubkey)

        lamports = resp.value
        sol = lamports / 1_000_000_000

        return jsonify({
            "success": True,
            "balance": sol
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/activity")
def activity():

    try:

        pubkey = Pubkey.from_string(WALLET_ADDRESS)

        sigs = client.get_signatures_for_address(
            pubkey,
            limit=10
        ).value

        items = []

        RPC_URL = "https://api.devnet.solana.com"

        for s in sigs:

            sig = str(s.signature)

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    sig,
                    {
                        "encoding": "json",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            }

            r = requests.post(RPC_URL, json=payload)

            tx_resp = r.json()

            tx = tx_resp.get("result")

            if not tx:
                continue

            meta = tx.get("meta")

            if not meta:
                continue

            tx_type = "unknown"
            amount = 0
            symbol = "SOL"

            # ====================================
            # SPL TOKEN TRANSFERS
            # ====================================

            pre_token_balances = meta.get(
                "preTokenBalances",
                []
            )

            post_token_balances = meta.get(
                "postTokenBalances",
                []
            )

            token_found = False

            if post_token_balances:

                for post_bal in post_token_balances:

                    owner = post_bal.get("owner")

                    if owner != WALLET_ADDRESS:
                        continue

                    token_found = True

                    mint = post_bal.get("mint")

                    post_amt = float(
                        post_bal["uiTokenAmount"]["uiAmount"]
                        or 0
                    )

                    pre_amt = 0

                    for pre_bal in pre_token_balances:

                        if (
                            pre_bal.get("owner")
                            == WALLET_ADDRESS
                            and
                            pre_bal.get("mint")
                            == mint
                        ):

                            pre_amt = float(
                                pre_bal["uiTokenAmount"]["uiAmount"]
                                or 0
                            )

                            break

                    diff = post_amt - pre_amt

                    if diff > 0:
                        tx_type = "receive"
                        amount = diff

                    elif diff < 0:
                        tx_type = "send"
                        amount = abs(diff)

            # ====================================
            # SOL TRANSFER FALLBACK
            # ====================================

            if not token_found:

                pre_balances = meta.get(
                    "preBalances",
                    []
                )

                post_balances = meta.get(
                    "postBalances",
                    []
                )

                account_keys = (
                    tx["transaction"]["message"]
                    ["accountKeys"]
                )

                wallet_index = None

                for i, key in enumerate(account_keys):

                    if isinstance(key, dict):
                        addr = key.get("pubkey")
                    else:
                        addr = key

                    if addr == WALLET_ADDRESS:
                        wallet_index = i
                        break

                if wallet_index is None:
                    continue

                pre = pre_balances[wallet_index]
                post = post_balances[wallet_index]

                diff_lamports = post - pre

                amount = (
                    abs(diff_lamports)
                    / 1_000_000_000
                )

                tx_type = (
                    "receive"
                    if diff_lamports > 0
                    else "send"
                )

            items.append({
                "signature": sig,
                "amount": round(amount, 4),
                "time": s.block_time,
                "type": tx_type,
                "symbol": symbol
            })

        return jsonify({
            "success": True,
            "activity": items
        })

    except Exception as e:

        print("ACTIVITY ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        })
        
if __name__ == "__main__":
    app.run(debug=True)