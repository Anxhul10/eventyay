import pytest
import stripe
from unittest.mock import patch
from django.core.exceptions import ValidationError
from unittest.mock import patch
from functools import wraps
import stripe.error as stripe_err
# def handle_stripe_errors(operation_name: str):
#     """
#     Handle the Stripe errors.
#     @param operation_name: A string representing the operation name.
#     @return: A decorator function.
#     """

#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             try:
#                 return func(*args, **kwargs)
#             except stripe.error.APIError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='api_error', backend='stripe')
#                 logger.error('Stripe API error during %s: %s', operation_name, e)
#                 raise ValidationError('Stripe service error.')
#             except stripe.error.APIConnectionError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='connection_error', backend='stripe')
#                 logger.error('API connection error during %s: %s', operation_name, e)
#                 raise ValidationError('Network communication error.')
#             except stripe.error.AuthenticationError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='auth_error', backend='stripe')
#                 logger.error('Authentication error during %s: %s', operation_name, e)
#                 raise ValidationError(
#                     'Authentication failed. Please contact the administrator to check the configuration of the Stripe API key.'
#                 )
#             except stripe.error.CardError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='card_error', backend='stripe')
#                 logger.error('Card error during %s: %s', operation_name, e)
#                 raise ValidationError('Card error.')
#             except stripe.error.RateLimitError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='rate_limit', backend='stripe')
#                 logger.error('Rate limit error during %s: %s', operation_name, e)
#                 raise ValidationError('Too many requests. Please try again later.')
#             except stripe.error.InvalidRequestError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='invalid_request', backend='stripe')
#                 logger.error('Invalid request error during %s: %s', operation_name, e)
#                 raise ValidationError('Invalid request.')
#             except stripe.error.SignatureVerificationError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='signature_error', backend='stripe')
#                 logger.error('Signature verification failed during %s: %s', operation_name, e)
#                 raise ValidationError('Webhook signature verification failed.')
#             except stripe.error.PermissionError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='permission_error', backend='stripe')
#                 logger.error('Permission error during %s: %s', operation_name, e)
#                 raise ValidationError('Permission denied.')
#             except stripe.error.IdempotencyError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='idempotency_error', backend='stripe')
#                 logger.error('Idempotency error during %s: %s', operation_name, e)
#                 raise ValidationError('Idempotency error.')
#             except stripe.error.StripeError as e:
#                 log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code='stripe_error', backend='stripe')
#                 logger.error('Stripe error during %s: %s', operation_name, e)
#                 raise ValidationError('Payment processing error.')

#         return wrapper

#     return decorator

from functools import wraps
import stripe.error as stripe_err

# Format: (ExceptionClass, error_code, log_prefix, user_message)
STRIPE_ERRORS = [
    (stripe_err.CardError, 'card_error', 'Card error', 'Card error.'),
    (stripe_err.RateLimitError, 'rate_limit', 'Rate limit error', 'Too many requests. Please try again later.'),
    (stripe_err.InvalidRequestError, 'invalid_request', 'Invalid request error', 'Invalid request.'),
    (stripe_err.AuthenticationError, 'auth_error', 'Authentication error', 'Authentication failed. Please contact the administrator to check the configuration of the Stripe API key.'),
    (stripe_err.PermissionError, 'permission_error', 'Permission error', 'Permission denied.'),
    (stripe_err.APIConnectionError, 'connection_error', 'API connection error', 'Network communication error.'),
    (stripe_err.SignatureVerificationError, 'signature_error', 'Signature verification failed', 'Webhook signature verification failed.'),
    (stripe_err.IdempotencyError, 'idempotency_error', 'Idempotency error', 'Idempotency error.'),
    (stripe_err.APIError, 'api_error', 'Stripe API error', 'Stripe service error.'),
]

DEFAULT_ERROR = ('stripe_error', 'Stripe error', 'Payment processing error.')


def _resolve_stripe_error(exc: Exception) -> tuple[str, str, str]:
    """Match a Stripe exception to its (error_code, log_prefix, user_message)."""
    for exc_class, code, log_prefix, user_msg in STRIPE_ERRORS:
        if isinstance(exc, exc_class):
            return code, log_prefix, user_msg
    return DEFAULT_ERROR


def handle_stripe_errors(operation_name: str):
    """Catch, log, and translate Stripe exceptions into ValidationErrors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except stripe_err.StripeError as e:
                code, log_prefix, user_msg = _resolve_stripe_error(e)

                log_event('plugins', 'connection.stripe', OUTCOME_FAILURE, error_code=code, backend='stripe')
                logger.error('%s during %s: %s', log_prefix, operation_name, e)
                raise ValidationError(user_msg) from e

        return wrapper
    return decorator

def test_successful_operation():
    @handle_stripe_errors("test_operation")
    def operation():
        return "Success"

    assert operation() == "Success"


def test_stripe_api_error():
    @handle_stripe_errors("test_operation")
    def operation():
        raise stripe.error.APIError("API failed")

    with patch("eventyay.helpers.temp.log_event", create=True), \
         patch("eventyay.helpers.temp.logger", create=True), \
         patch("eventyay.helpers.temp.OUTCOME_FAILURE", "failure", create=True):
        with pytest.raises(ValidationError, match="Stripe service error."):
            operation()