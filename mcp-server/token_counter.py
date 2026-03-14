from functools import lru_cache

# from transformers import AutoTokenizer
import tiktoken

# @lru_cache(maxsize=4)
# def _get_tokenizer(model: str) -> AutoTokenizer:
#     return AutoTokenizer.from_pretrained(model)


# def count_tokens(text: str, model: str) -> int:
#     """
#     Count the number of tokens in a text for a given model.

#     Args:
#         text: The text to tokenize.
#         model: The HuggingFace model identifier.

#     Returns:
#         The number of tokens.
#     """
#     tokenizer = _get_tokenizer(model)
#     tokens = tokenizer(text)
#     return len(tokens["input_ids"])


@lru_cache(maxsize=4)
def _get_tokenizer(model: str) -> tiktoken.Encoding:
    """Load and cache a tiktoken encoding."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback sur cl100k_base pour les modèles non-OpenAI
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count the number of tokens in a text for a given model.

    Args:
        text: The text to tokenize.
        model: The model or encoding name.

    Returns:
        The number of tokens.
    """
    enc = _get_tokenizer(model)
    return len(enc.encode(text))
