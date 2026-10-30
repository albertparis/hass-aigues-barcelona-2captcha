"""Constants definition."""

DOMAIN = "aigues_barcelona"

CONF_CONTRACT = "contract"
CONF_VALUE = "value"
CONF_2CAPTCHA_APIKEY = "twocaptcha_api_key"
CONF_IMPORT_INVOICES = "import_invoices"

ATTR_LAST_MEASURE = "Last measure"

DEFAULT_SCAN_PERIOD = 28800  # 8 hours
INVOICE_CHECK_PERIOD = 86400  # 1 day
INVOICE_LOOKBACK_MONTHS = 36

API_HOST = "api.aiguesdebarcelona.cat"
API_COOKIE_TOKEN = "ofexTokenJwt"

API_ERROR_TOKEN_REVOKED = "JWT Token Revoked"
API_ERROR_TOKEN_INVALID = "Invalid JWT"

RECAPTCHA_V2_PAGEURL = "https://www.aiguesdebarcelona.cat/es/area-clientes#/login"
RECAPTCHA_V2_SITEKEY = "6LfPoasUAAAAAL5M1txzF5PJ91udHgE5PMm0JWWS"

# Statistics IDs
STAT_ID_CONSUMPTION = lambda contract_id: f"{DOMAIN}:{contract_id}_consumption"
STAT_ID_COST = lambda contract_id: f"{DOMAIN}:{contract_id}_cost"
