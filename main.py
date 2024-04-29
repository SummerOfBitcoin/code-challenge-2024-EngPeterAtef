import json
import hashlib
import os
import time
import sys

MIN_OUTPUT_VALUE = 0
MAX_OUTPUT_VALUE = 21_000_000
MAX_BLOCK_SIZE = 4_000_000
MAX_VOUT = 2**32 - 1
# to calculate the block size in weight units, we need to multiply the fields by the following multipliers
"""
Field	Multiplier
version	x4
marker	x1
flag	x1
input	x4
output	x4
witness	x1
locktime	x4
"""


def validate_transaction(transaction: dict) -> bool:
    # Add your validation logic here
    # For example, you can check if the transaction has required fields
    # You can also check if inputs and outputs are valid, etc.
    # For example, check if sender has sufficient balance, signature is valid, etc.
    # For simplicity, let's assume all transactions are valid in this example
    """Validate a transaction from the mempool.

    Args:
        transaction (dict): transaction data as a dictionary.

    Returns:
        bool: True if the transaction is valid, False otherwise.
    """
    # Neither lists of inputs or outputs are empty.
    if not transaction["vin"] or not transaction["vout"]:
        return False
    # The transaction size in bytes is less than MAX_BLOCK_SIZE.
    # TODO: calculate the transaction size in weight units
    # Each output value, as well as the total, must be within the allowed range of values (less than 21m coins, more than 0).
    total = 0
    for output in transaction["vout"]:
        value = output["value"]
        if value < MIN_OUTPUT_VALUE or value > MAX_OUTPUT_VALUE:
            return False
        total += value
    if total > MAX_OUTPUT_VALUE or total < MIN_OUTPUT_VALUE:
        return False
    # None of the inputs have hash=0, N=–1 (coinbase transactions should not be relayed).
    for input in transaction["vin"]:
        if input["txid"] == "0" and input["vout"] == -1:
            return False
    # locktime is less than or equal to INT_MAX.
    if transaction["locktime"] > sys.maxsize or transaction["locktime"] < 0:
        return False
    # The transaction size in bytes is greater than or equal to 100.
    transaction_size_bytes = len(json.dumps(transaction))
    if transaction_size_bytes < 100:
        return False


# Function to read JSON files from the mempool folder
def read_transactions_from_mempool():
    """This function reads the transaction data from the mempool folder and returns a list of transactions.

    Returns:
        list: list of transactions read from the mempool folder.
    """
    transactions = []
    mempool_dir = "mempool"
    for filename in os.listdir(mempool_dir):
        if filename.endswith(".json"):
            with open(os.path.join(mempool_dir, filename), "r") as f:
                # read the transaction data as dictionary
                data = json.load(f)
                # get the hash of the transaction and set it as txid
                data["txid"] = hashlib.sha256(json.dumps(data).encode()).hexdigest()
                # append the transaction to the list
                transactions.append(data)
    return transactions


# Function to serialize a transaction
def serialize_transaction(transaction):
    return json.dumps(transaction, sort_keys=True)


# Function to create a coinbase transaction
def create_coinbase_transaction():
    """This function creates a coinbase transaction with a reward of 50 BTC for mining a block.
        it must be the first transaction in the block.
        It must only contain one input with txid=0 and vout=MAX_VOUT.
    Returns:
        dict: coinbase transaction as a dictionary.
    """
    return {
        "version": 2,
        "locktime": 0,
        "txid": "coinbase_txid_placeholder",
        "vin": [
            {
                "txid": 0,
                "vout": MAX_VOUT,
                "prevout": {
                    "scriptpubkey": "coinbase_scriptpubkey",
                    "value": 50,
                },
            }
        ],
        "vout": [
            {
                "scriptpubkey": "coinbase_scriptpubkey",
                "value": 50,
            }
        ],
    }


# Function to construct the block header
def construct_block_header(transactions, prev_block_hash, nonce):
    """This function constructs the block header.
    it takes list of transactions, previous block hash, and nonce as input and returns the block header.

    Args:
        transactions (list): list of transactions will be included in the block.
        prev_block_hash (str): hash of the previous block in the blockchain.
        nonce (int): nonce value used in mining the block.

    Returns:
        dict: block header containing version, previous block hash, merkle root, time, and nonce.
    """
    # Combine all transaction IDs
    txids = [transaction["txid"] for transaction in transactions]
    merkle_root = hashlib.sha256("".join(txids).encode()).hexdigest()
    # version is 4 bytes number in little-endian
    version = 2
    # Construct the block header
    block_header = {
        "version": version,
        "prev_block_hash": prev_block_hash,  # TODO: reverse theprev_block_hash
        "merkle_root": merkle_root,  # TODO: reverse the merkle root
        "time": int(time.time()),
        "nonce": nonce,
    }
    return block_header


# Function to mine the block
# def mine_block(transactions, prev_block_hash, difficulty_target):
#     nonce = 0
#     while True:
#         # construct the block header
#         block_header = construct_block_header(transactions, prev_block_hash, nonce)
#         # hash the block header as a hexadecimal string
#         block_hash = hashlib.sha256(
#             # convert the block header to JSON string and encode it
#             json.dumps(block_header, sort_keys=True).encode()
#         ).hexdigest()
#         # check if the block hash is less than the difficulty target
#         if block_hash < difficulty_target:
#             return block_header, block_hash
#         nonce += 1


def mining(target, transactions):
    """This function mines a block by finding a hash that is less than the target.

    Args:
        target (str): the target hash value that the block hash should be less than.
        transactions (list): list of transactions to include in the block.
    Returns:
        tuple: a tuple containing the block header and the block hash.
    """

    # The hash function used in mining (convert hexadecimal to binary first, then SHA256 twice)
    def hash256(data):
        binary = bytes.fromhex(data)
        hash1 = hashlib.sha256(binary).digest()
        hash2 = hashlib.sha256(hash1).hexdigest()
        return hash2

    # Convert a number to fit inside a field that is a specific number of bytes e.g. field(1, 4) = 00000001
    def field(data, size):
        return format(data, "0{}x".format(size * 2))

    # Reverse the order of bytes (often happens when working with raw bitcoin data)
    def reversebytes(data):
        return "".join(reversed([data[i : i + 2] for i in range(0, len(data), 2)]))

    # ------------
    # Block Header
    # ------------

    # Block Header (Fields)
    version = 2
    prevblock = "000000000002d01c1fccc21636b607dfd930d31d01c3a62104612a1719011250"
    time_stamp = int(time.time())  # 0x5db8c0ff
    # bits = "1b04864c"
    nonce = 0  # 274148111
    txids = [transaction["txid"] for transaction in transactions]
    merkleroot = hashlib.sha256("".join(txids).encode()).hexdigest()
    # Block Header (Serialized)
    header = (
        reversebytes(field(version, 4))
        + reversebytes(prevblock)
        + reversebytes(merkleroot)
        + reversebytes(field(time_stamp, 4))
        # + reversebytes(bits)
    )

    # -----
    # Mine!
    # -----
    while True:
        # hash the block header
        attempt = header + reversebytes(field(nonce, 4))
        result = reversebytes(hash256(attempt))

        # show result
        # print(f"{nonce}: {result}")

        # end if we get a block hash below the target
        if int(result, 16) < int(target, 16):
            return header, result

        # increment the nonce and try again...
        nonce += 1


# Main function
def main():
    # Read transactions from mempool folder
    transactions = read_transactions_from_mempool()

    # Validate transactions and filter out invalid ones
    valid_transactions = [tx for tx in transactions if validate_transaction(tx)]
    # get the transaction count
    transaction_count = len(valid_transactions)
    print(f"Valid transactions: {transaction_count}")
    # Create the coinbase transaction
    coinbase_tx = create_coinbase_transaction()

    # Add coinbase transaction to the list of transactions
    transactions_for_block = [coinbase_tx] + valid_transactions

    # Define previous block hash and difficulty target
    difficulty_target = (
        "0000ffff00000000000000000000000000000000000000000000000000000000"
    )

    # Mine the block
    # block_header, block_hash = mine_block(
    #     transactions_for_block, prev_block_hash, difficulty_target
    # )
    block_header, block_hash = mining(difficulty_target, transactions_for_block)

    # Write the mined block to output.txt
    with open("output.txt", "w") as f:
        f.write(json.dumps(block_header, indent=4, sort_keys=True) + "\n")
        f.write(serialize_transaction(coinbase_tx) + "\n")
        for tx in valid_transactions:
            f.write(tx["txid"] + "\n")


if __name__ == "__main__":
    main()
