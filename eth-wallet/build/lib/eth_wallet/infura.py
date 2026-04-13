from web3 import (
    Web3,
    HTTPProvider,
)
from eth_wallet.exceptions import (
    InfuraErrorException
)
import os


# TODO: for API KEY use dotenv or environment variables
# TODO: create new project with different API key this API KEY is already uploaded on Github
class Infura:
    """Abstraction over Infura node connection."""

    def __init__(self):
        self.w3 = Web3(HTTPProvider("https://sepolia.infura.io/v3/b91de17a0d2340318cb6078269544928"))
        # Now uses environment variable if set

    def get_web3(self):
        if not self.w3.is_connected():
            raise InfuraErrorException()

        return self.w3
