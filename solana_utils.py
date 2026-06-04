import base64
import base58
from solders.pubkey import Pubkey
from solders.message import MessageV0
from solders.signature import Signature
from solana.rpc.api import Client
from solders.system_program import transfer, TransferParams

LAMPORTS_PER_SOL = 1_000_000_000
client = Client("https://api.devnet.solana.com")
ESP32_WALLET = "oggYcXGKBcEWB25SiRfBd6iCHE6dB6xkB2bzgfkxdTc"
# ESP32_WALLET ="<put-your-generated-wallets-publicKey-here>"

def create_tx(recipient: str, amount_sol: float):
    sender = Pubkey.from_string(ESP32_WALLET)
    receiver = Pubkey.from_string(recipient)
    blockhash = client.get_latest_blockhash().value.blockhash

    ix = transfer(
        TransferParams(
            from_pubkey=sender,
            to_pubkey=receiver,
            lamports=int(amount_sol * LAMPORTS_PER_SOL),
        )
    )

    msg = MessageV0.try_compile(
        payer=sender,
        instructions=[ix],
        recent_blockhash=blockhash,
        address_lookup_table_accounts=[]
    )

    # 0x80 is the v0 version prefix — Solana verifies signatures against
    # the full versioned message bytes INCLUDING this prefix
    versioned_msg_bytes = bytes([0x80]) + bytes(msg)

    return {
        "message_bytes": base64.b64encode(versioned_msg_bytes).decode(),
        "msg_object": msg,
    }

def build_signed_tx(message_bytes_b64: str, signature_b58: str, msg_object=None):
    sig = Signature.from_string(signature_b58)
    sig_bytes = bytes(sig)

    # message_bytes already includes 0x80 prefix (152 bytes)
    msg_bytes = base64.b64decode(message_bytes_b64)

    # Wire format: [0x01 num_sigs][64 sig bytes][0x80 + message body]
    raw_tx = bytes([0x01]) + sig_bytes + msg_bytes
    return raw_tx