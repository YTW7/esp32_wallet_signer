from solders.keypair import Keypair
import base58

TARGET_PREFIX = "og"

attempts = 0

while True:
    kp = Keypair()

    pubkey = str(kp.pubkey())

    attempts += 1

    if pubkey.startswith(TARGET_PREFIX):

        print("=== MATCH FOUND ===")
        print()

        print("Attempts:", attempts)

        print()
        print("Public Key:")
        print(pubkey)

        print()
        print("Private Key Bytes:")
        print(list(bytes(kp)))

        print()
        print("Private Key Base58:")
        print(base58.b58encode(bytes(kp)).decode())

        break

    if attempts % 10000 == 0:
        print(f"Attempts: {attempts}")