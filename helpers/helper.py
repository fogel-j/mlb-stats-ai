import tiktoken

def num_tokens(string: str) -> int:
    """Returns the number of tokens in a text string"""
    encoding = tiktoken.encoding_for_model("gpt-4")
    num_tokens = len(encoding.encode(str(string)))
    return num_tokens