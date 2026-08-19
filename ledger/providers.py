import uuid
from decimal import Decimal

class PaymentProviderInterface:
    """
    Abstract interface for integrating with payment providers.
    """
    def create_virtual_account(self, user):
        raise NotImplementedError

    def initiate_transfer(self, amount, to_account_details, reference):
        raise NotImplementedError

    def verify_transaction(self, reference):
        raise NotImplementedError


class DummyProvider(PaymentProviderInterface):
    """
    Dummy provider for sandbox/testing. 
    Simulates successful interactions with a banking provider.
    """
    def create_virtual_account(self, user):
        """
        Simulates the creation of a virtual bank account.
        """
        return {
            "status": "success",
            "account_number": str(uuid.uuid4().int)[:10],
            "bank_name": "Nexus Sandbox Bank",
            "account_name": user.get_full_name() or user.email
        }

    def initiate_transfer(self, amount, to_account_details, reference):
        """
        Simulates initiating an outbound transfer.
        Always returns pending. The mock webhook will later resolve it.
        """
        return {
            "status": "pending",
            "reference": reference,
            "provider_message": "Transfer queued for processing."
        }

    def verify_transaction(self, reference):
        """
        Simulates verifying a transaction.
        For dummy provider, we always return success if the reference exists.
        """
        return {
            "status": "success",
            "reference": reference,
            "amount": Decimal("0.00"), # Simulated actual amount
            "provider_message": "Transaction successful."
        }

# Provider instance
default_provider = DummyProvider()
