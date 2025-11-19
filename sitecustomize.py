"""
Site customization to disable SSL verification for all Python SSL connections.
This is used in environments with SSL/TLS inspection.
WARNING: This disables SSL verification globally and should only be used in controlled environments.
"""
import os
import pathlib
import ssl
import sys

# Disable SSL verification globally
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

# Set environment variables for requests library
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Ensure pip picks up the co-located insecure pip.conf when present
pip_conf = pathlib.Path(__file__).with_name("pip.conf")
if pip_conf.exists():
    os.environ.setdefault("PIP_CONFIG_FILE", str(pip_conf))

# Monkey-patch urllib3 to disable SSL verification (for Poetry and other tools)
def _patch_urllib3_on_import():
    """Patch urllib3.util.ssl_ to disable SSL verification."""
    try:
        from urllib3.util import ssl_
        import warnings
        from urllib3 import exceptions

        # Disable warnings
        warnings.filterwarnings('ignore', category=exceptions.InsecureRequestWarning)
        try:
            import urllib3
            urllib3.disable_warnings(exceptions.InsecureRequestWarning)
        except:
            pass

        # Monkey-patch create_urllib3_context to disable verification
        original_create_urllib3_context = ssl_.create_urllib3_context

        def patched_create_urllib3_context(
            ssl_version=None,
            cert_reqs=None,
            options=None,
            ciphers=None,
            ssl_minimum_version=None,
            ssl_maximum_version=None,
        ):
            # Force CERT_NONE to disable verification
            cert_reqs = ssl.CERT_NONE
            context = original_create_urllib3_context(
                ssl_version=ssl_version,
                cert_reqs=cert_reqs,
                options=options,
                ciphers=ciphers,
                ssl_minimum_version=ssl_minimum_version,
                ssl_maximum_version=ssl_maximum_version,
            )
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        ssl_.create_urllib3_context = patched_create_urllib3_context
        return True
    except ImportError:
        return False  # urllib3 not installed

# Try to patch urllib3 immediately if available
_patch_urllib3_on_import()
