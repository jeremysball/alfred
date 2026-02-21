"""Sandbox builtins for safe job execution.

Provides a restricted set of Python builtins for user-submitted job code.
"""

# Safe builtins for sandboxed job execution
SANDBOX_BUILTINS = {
    # Basic types
    "print": print,
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "type": type,
    # Iteration
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    # Math
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "pow": pow,
    "divmod": divmod,
    # Type checking
    "isinstance": isinstance,
    "issubclass": issubclass,
    "hasattr": hasattr,
    "getattr": getattr,
    "setattr": setattr,
    # Encoding
    "chr": chr,
    "ord": ord,
    "hex": hex,
    "bin": bin,
    "oct": oct,
    "format": format,
    "repr": repr,
    # Logic
    "any": any,
    "all": all,
    # Exceptions (safe subset)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,
    "ImportError": ImportError,
    "NameError": NameError,
    "TimeoutError": TimeoutError,
}
