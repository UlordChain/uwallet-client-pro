UWallet_VERSION = '1.0.5'  # version of the client package
PROTOCOL_VERSION = '0.10'   # protocol version requested

OLD_SEED_VERSION = 4        # electrum versions < 2.0
NEW_SEED_VERSION = 11       # electrum versions >= 2.0
FINAL_SEED_VERSION = 12     # electrum >= 2.7 will set this to prevent
                            # old versions from overwriting new format


# The hash of the mnemonic seed must begin with this
SEED_PREFIX      = '01'      # Electrum standard wallet
SEED_PREFIX_2FA  = '101'     # extended seed for two-factor authentication
