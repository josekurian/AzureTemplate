from azure.identity import DefaultAzureCredential

_credential = None

def get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return _credential
