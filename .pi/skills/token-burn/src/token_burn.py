#!/usr/bin/env python3
"""
token-burn: Calculate token usage from pi session JSONL files.

Streams through JSONL files in buffered chunks to handle large files
without loading into memory. Extracts actual token counts from message metadata
including cached tokens (cacheRead, cacheWrite).
"""

import json
import sys
import os
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Iterator, Tuple, Optional


def stream_jsonl_lines(filepath: str, buffer_size: int = 8192) -> Iterator[str]:
    """Stream lines from a JSONL file using buffered reading."""
    with open(filepath, 'r', encoding='utf-8') as f:
        buffer = ''
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                if buffer.strip():
                    yield buffer.strip()
                break
            
            buffer += chunk
            lines = buffer.split('\n')
            buffer = lines[-1]
            
            for line in lines[:-1]:
                if line.strip():
                    yield line.strip()


def extract_model_info(data: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extract model provider and ID from pi session data structures."""
    msg = data.get('message', {})
    
    # In .pi format, provider and model are at the message level
    if msg:
        provider = msg.get('provider')
        model = msg.get('model')
        if provider and model:
            return provider, model
    
    # Check for model-snapshot custom events (if present in .pi)
    if data.get('type') == 'custom' and data.get('customType') == 'model-snapshot':
        snap = data.get('data', {})
        provider = snap.get('provider')
        model = snap.get('modelId')
        if provider and model:
            return provider, f"{provider}/{model}"
    
    return None, None


def extract_token_usage(data: dict) -> Tuple[int, int, int, int, int]:
    """
    Extract token usage from message data, including cached tokens.
    
    Returns: (input_tokens, output_tokens, cache_read, cache_write, total_tokens)
    """
    msg = data.get('message', {})
    usage = msg.get('usage', {})
    
    if usage:
        inp = usage.get('input', 0) or usage.get('inputTokens', 0) or 0
        out = usage.get('output', 0) or usage.get('outputTokens', 0) or 0
        cache_read = usage.get('cacheRead', 0) or 0
        cache_write = usage.get('cacheWrite', 0) or 0
        total = usage.get('totalTokens', 0) or (inp + out + cache_read + cache_write)
        return inp, out, cache_read, cache_write, total
    
    return 0, 0, 0, 0, 0


def get_model_name(provider: Optional[str], model_id: Optional[str]) -> str:
    """Generate canonical model name."""
    if provider and model_id:
        if '/' in model_id:
            return model_id
        return f"{provider}/{model_id}"
    elif model_id:
        return model_id
    elif provider:
        return provider
    return "unknown"


def get_model_emoji(model_name: str) -> str:
    """Get an appropriate emoji for a model/provider."""
    model_lower = model_name.lower()
    
    if 'kimi' in model_lower:
        return '🌙'
    elif 'claude' in model_lower or 'anthropic' in model_lower:
        return '🧠'
    elif 'gpt' in model_lower or 'openai' in model_lower:
        return '🤖'
    elif 'gemini' in model_lower or 'google' in model_lower:
        return '💎'
    elif 'glm' in model_lower or 'zai' in model_lower:
        return '⚡'
    elif 'llama' in model_lower or 'meta' in model_lower:
        return '🦙'
    elif 'deepseek' in model_lower:
        return '🔮'
    else:
        return '🤖'


def format_tokens(n: int) -> str:
    """Format token numbers with K/M suffix for readability."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    else:
        return str(n)


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def print_table_header(title: str, emoji: str = "📊"):
    """Print a beautiful table header."""
    width = 70
    print()
    print(f"╔{'═' * width}╗")
    print(f"║{emoji}  {title:<{width-4}}║")
    print(f"╠{'═' * width}╣")


def print_table_row(label: str, value: str, emoji: str = "  ", indent: int = 0):
    """Print a table row with consistent formatting."""
    width = 70
    spaces = " " * indent
    print(f"║{spaces}{emoji} {label:<20} {value:>42}{spaces} ║")


def print_table_separator():
    """Print a table separator line."""
    width = 70
    print(f"╠{'═' * width}╣")


def print_table_footer():
    """Print a table footer."""
    width = 70
    print(f"╚{'═' * width}╝")


def print_model_card(model: str, counts: dict, rank: int):
    """Print a beautiful model usage card."""
    emoji = get_model_emoji(model)
    total = counts['total']
    
    print()
    print(f"┌{'─' * 68}┐")
    print(f"│ #{rank:<2} {emoji}  {model:<55} │")
    print(f"├{'─' * 68}┤")
    
    # Input tokens
    inp = counts['input']
    inp_pct = (inp / total * 100) if total > 0 else 0
    print(f"│  📥  Input:        {format_number(inp):>15}  ({format_tokens(inp)})  {inp_pct:>5.1f}%  │")
    
    # Output tokens
    out = counts['output']
    out_pct = (out / total * 100) if total > 0 else 0
    print(f"│  📤  Output:       {format_number(out):>15}  ({format_tokens(out)})  {out_pct:>5.1f}%  │")
    
    # Cache read (if any)
    cache_r = counts['cache_read']
    if cache_r > 0:
        cache_r_pct = (cache_r / total * 100) if total > 0 else 0
        print(f"│  💾  Cache Read:   {format_number(cache_r):>15}  ({format_tokens(cache_r)})  {cache_r_pct:>5.1f}%  │")
    
    # Cache write (if any)
    cache_w = counts['cache_write']
    if cache_w > 0:
        cache_w_pct = (cache_w / total * 100) if total > 0 else 0
        print(f"│  💿  Cache Write:  {format_number(cache_w):>15}  ({format_tokens(cache_w)})  {cache_w_pct:>5.1f}%  │")
    
    print(f"├{'─' * 68}┤")
    print(f"│  🔥  TOTAL:        {format_number(total):>15}  ({format_tokens(total)})           │")
    print(f"└{'─' * 68}┘")


def process_jsonl_file(filepath: str, buffer_size: int = 8192) -> Dict:
    """Process a JSONL file and calculate token usage."""
    results = {
        'file': filepath,
        'lines_processed': 0,
        'messages_processed': 0,
        'tokens_by_model': defaultdict(lambda: {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0}),
        'errors': 0,
        'total_input': 0,
        'total_output': 0,
        'total_cache_read': 0,
        'total_cache_write': 0,
        'total_tokens': 0
    }
    
    current_model = None
    
    for line in stream_jsonl_lines(filepath, buffer_size):
        results['lines_processed'] += 1
        
        try:
            data = json.loads(line)
            msg_type = data.get('type')
            
            # Skip session metadata lines
            if msg_type == 'session':
                continue
            
            # Handle model-snapshot events
            if msg_type == 'custom' and data.get('customType') == 'model-snapshot':
                provider, model_id = extract_model_info(data)
                if model_id:
                    current_model = get_model_name(provider, model_id)
            
            # Handle message events with usage data
            if msg_type == 'message':
                provider, model_id = extract_model_info(data)
                if model_id:
                    current_model = get_model_name(provider, model_id)
                
                inp, out, cache_read, cache_write, total = extract_token_usage(data)
                
                if total > 0:
                    results['messages_processed'] += 1
                    model = current_model or "unknown"
                    
                    results['tokens_by_model'][model]['input'] += inp
                    results['tokens_by_model'][model]['output'] += out
                    results['tokens_by_model'][model]['cache_read'] += cache_read
                    results['tokens_by_model'][model]['cache_write'] += cache_write
                    results['tokens_by_model'][model]['total'] += total
                    
                    results['total_input'] += inp
                    results['total_output'] += out
                    results['total_cache_read'] += cache_read
                    results['total_cache_write'] += cache_write
                    results['total_tokens'] += total
                    
        except Exception as e:
            results['errors'] += 1
            if results['errors'] <= 3:
                print(f"⚠️  Warning: Error processing line in {filepath}: {e}", file=sys.stderr)
    
    results['tokens_by_model'] = dict(results['tokens_by_model'])
    return results


def find_session_files(base_path: str) -> list:
    """Find all JSONL session files in a directory."""
    base = Path(base_path)
    files = []
    for pattern in ['**/*.jsonl', '**/*.jsonl.gz']:
        files.extend(base.glob(pattern))
    return sorted(files)


def get_default_sessions_path() -> str:
    """Get the default pi sessions path."""
    home = Path.home()
    return str(home / '.pi' / 'agent' / 'sessions')


def main():
    default_path = get_default_sessions_path()
    
    parser = argparse.ArgumentParser(
        description='🔥 Calculate token usage from pi session JSONL files',
        epilog=f'Example: token-burn.py {default_path} --recursive'
    )
    
    parser.add_argument('path', nargs='?', default=default_path, 
                        help=f'Path to JSONL file or directory (default: {default_path})')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Recursively process directory')
    parser.add_argument('-j', '--json', action='store_true', 
                        help='Output as JSON')
    
    args = parser.parse_args()
    
    input_path = Path(args.path)
    
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        if args.recursive:
            files = find_session_files(str(input_path))
        else:
            files = list(input_path.glob('*.jsonl'))
    else:
        print(f"❌ Error: Path not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    if not files:
        print(f"❌ No JSONL files found in {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # Process files
    all_results = []
    grand_total = defaultdict(lambda: {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0})
    total_lines = 0
    total_messages = 0
    
    for filepath in files:
        try:
            result = process_jsonl_file(str(filepath))
            all_results.append(result)
            
            for model, counts in result['tokens_by_model'].items():
                grand_total[model]['input'] += counts['input']
                grand_total[model]['output'] += counts['output']
                grand_total[model]['cache_read'] += counts['cache_read']
                grand_total[model]['cache_write'] += counts['cache_write']
                grand_total[model]['total'] += counts['total']
            
            total_lines += result['lines_processed']
            total_messages += result['messages_processed']
            
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
    
    # Output results
    if args.json:
        output = {
            'files_processed': len(files),
            'total_lines': total_lines,
            'total_messages': total_messages,
            'tokens_by_model': {k: dict(v) for k, v in grand_total.items()},
            'total_input': sum(m['input'] for m in grand_total.values()),
            'total_output': sum(m['output'] for m in grand_total.values()),
            'total_cache_read': sum(m['cache_read'] for m in grand_total.values()),
            'total_cache_write': sum(m['cache_write'] for m in grand_total.values()),
            'total_tokens': sum(m['total'] for m in grand_total.values()),
        }
        print(json.dumps(output, indent=2))
    else:
        # Beautiful table output with emojis
        print()
        print("🔥" + "═" * 68 + "🔥")
        print("║" + " " * 20 + "💰 TOKEN BURN REPORT 💰" + " " * 21 + "║")
        print("🔥" + "═" * 68 + "🔥")
        
        # Summary section
        print_table_header("📈 Session Summary")
        print_table_row("Files Processed", format_number(len(files)), "📁")
        print_table_row("Total Lines", format_number(total_lines), "📄")
        print_table_row("Messages w/ Usage", format_number(total_messages), "💬")
        print_table_footer()
        
        # Model breakdown
        sorted_models = sorted(grand_total.items(), key=lambda x: -x[1]['total'])
        
        print()
        print("📊" + "═" * 68 + "📊")
        print("║" + " " * 15 + "🤖 TOKEN USAGE BY MODEL 🤖" + " " * 18 + "║")
        print("📊" + "═" * 68 + "📊")
        
        for rank, (model, counts) in enumerate(sorted_models, 1):
            print_model_card(model, counts, rank)
        
        # Grand totals
        print()
        print("💰" + "═" * 68 + "💰")
        print("║" + " " * 20 + "🏆 GRAND TOTALS 🏆" + " " * 24 + "║")
        print("💰" + "═" * 68 + "💰")
        
        total_in = sum(m['input'] for m in grand_total.values())
        total_out = sum(m['output'] for m in grand_total.values())
        total_cache_r = sum(m['cache_read'] for m in grand_total.values())
        total_cache_w = sum(m['cache_write'] for m in grand_total.values())
        total_all = sum(m['total'] for m in grand_total.values())
        
        print(f"│  📥  TOTAL INPUT         {format_number(total_in):>15}  ({format_tokens(total_in)})          │")
        print(f"│  📤  TOTAL OUTPUT        {format_number(total_out):>15}  ({format_tokens(total_out)})          │")
        
        if total_cache_r > 0:
            print(f"│  💾  TOTAL CACHE READ    {format_number(total_cache_r):>15}  ({format_tokens(total_cache_r)})          │")
        if total_cache_w > 0:
            print(f"│  💿  TOTAL CACHE WRITE   {format_number(total_cache_w):>15}  ({format_tokens(total_cache_w)})          │")
        
        print("├" + "─" * 68 + "┤")
        print(f"│  🔥  GRAND TOTAL         {format_number(total_all):>15}  ({format_tokens(total_all)})          │")
        print("└" + "─" * 68 + "┘")
        
        # Cost estimation tip
        print()
        print("💡" + "─" * 68 + "💡")
        print("│  💰 Cost Estimation Tip:                                            │")
        print("│     Use serper-search or web-search to find current pricing:        │")
        print("│     'Anthropic Claude API pricing per token 2025'                   │")
        print("│     'OpenAI GPT-4 pricing per token 2025'                           │")
        print("│     Then multiply: tokens × price_per_token = estimated cost        │")
        print("💡" + "─" * 68 + "💡")
        print()


if __name__ == '__main__':
    main()
