#!/usr/bin/env python3
"""
🔥 Token Burn - Calculate token usage from pi session JSONL files
with beautiful emoji-enhanced tables.

Extracts actual token counts including cached tokens (cacheRead, cacheWrite)
from message metadata.
"""

import json
import sys
import argparse
import shutil
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any


# Provider emoji mapping
PROVIDER_EMOJIS = {
    'kimi': '🌙',
    'claude': '🧠',
    'anthropic': '🧠',
    'openai': '🤖',
    'gemini': '💎',
    'google': '💎',
    'glm': '⚡',
    'zhipu': '⚡',
    'zai': '⚡',
    'deepseek': '🔮',
    'qwen': '🐉',
    'alibaba': '🐉',
}


def get_provider_emoji(model: str) -> str:
    """Get emoji for a model based on provider."""
    model_lower = model.lower()
    for provider, emoji in PROVIDER_EMOJIS.items():
        if provider in model_lower:
            return emoji
    return '🤖'


def format_number(n: int) -> str:
    """Format number with commas."""
    return f"{n:,}"


def format_tokens(n: int) -> str:
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def get_terminal_width() -> int:
    """Get terminal width with fallback."""
    return shutil.get_terminal_size((80, 20)).columns


def process_jsonl_file(filepath: str) -> Dict[str, Any]:
    """Process a single JSONL file and extract token usage."""
    result = {
        'tokens_by_model': defaultdict(lambda: {
            'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0,
            'total': 0
        }),
        'lines_processed': 0,
        'messages_processed': 0,
    }
    
    with open(filepath, 'r') as f:
        for line in f:
            result['lines_processed'] += 1
            try:
                data = json.loads(line)
                
                # Only process assistant messages with usage data
                if (data.get('type') == 'message' and 
                    data.get('message', {}).get('role') == 'assistant'):
                    
                    message = data['message']
                    model = message.get('model', 'unknown')
                    provider = message.get('provider', 'unknown')
                    full_model = f"{provider}/{model}" if provider else model
                    
                    usage = message.get('usage', {})
                    
                    input_tokens = usage.get('input', 0)
                    output_tokens = usage.get('output', 0)
                    cache_read = usage.get('cacheRead', 0)
                    cache_write = usage.get('cacheWrite', 0)
                    
                    result['tokens_by_model'][full_model]['input'] += input_tokens
                    result['tokens_by_model'][full_model]['output'] += output_tokens
                    result['tokens_by_model'][full_model]['cache_read'] += cache_read
                    result['tokens_by_model'][full_model]['cache_write'] += cache_write
                    result['tokens_by_model'][full_model]['total'] += (
                        input_tokens + output_tokens + cache_read + cache_write
                    )
                    result['messages_processed'] += 1
                    
            except json.JSONDecodeError:
                continue
    
    return result


def find_session_files(base_path: str) -> list:
    """Find all JSONL files recursively."""
    base = Path(base_path)
    files = []
    for pattern in ['**/*.jsonl', '**/*.jsonl.gz']:
        files.extend(base.glob(pattern))
    return sorted(files)


def get_default_sessions_path() -> str:
    """Get the default pi sessions path."""
    home = Path.home()
    return str(home / '.pi' / 'agent' / 'sessions')


def print_box(title: str, emoji: str, width: int):
    """Print a box header with title."""
    padding = width - len(title) - len(emoji) - 5  # 5 for ║ spaces and spacing
    print(f"{emoji}{'═' * (width - 2)}{emoji}")
    print(f"║{' ' * ((width - len(title) - 2) // 2)}{title}{' ' * ((width - len(title) - 2) // 2 + (width - len(title) - 2) % 2)}║")
    print(f"{emoji}{'═' * (width - 2)}{emoji}")


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
    grand_total = defaultdict(lambda: {
        'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0
    })
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
            'tokens_by_model': {},
            'total_input': sum(m['input'] for m in grand_total.values()),
            'total_output': sum(m['output'] for m in grand_total.values()),
            'total_cache_read': sum(m['cache_read'] for m in grand_total.values()),
            'total_cache_write': sum(m['cache_write'] for m in grand_total.values()),
            'total_tokens': sum(m['total'] for m in grand_total.values()),
        }
        
        for model, counts in grand_total.items():
            output['tokens_by_model'][model] = dict(counts)
        
        print(json.dumps(output, indent=2))
    else:
        # Get terminal width
        width = get_terminal_width()
        
        # Minimum width for readable output
        width = max(width, 60)
        
        # Beautiful table output with emojis
        print()
        print("🔥" + "═" * (width - 4) + "🔥")
        title = "💰 TOKEN BURN REPORT 💰"
        print("║" + " " * ((width - len(title) - 2) // 2) + title + " " * ((width - len(title) - 2) // 2 + (width - len(title) - 2) % 2) + "║")
        print("🔥" + "═" * (width - 4) + "🔥")
        
        # Summary section
        print()
        print("╔" + "═" * (width - 2) + "╗")
        summary_title = "📊 Session Summary"
        print("║" + " " * ((width - len(summary_title) - 2) // 2) + summary_title + " " * ((width - len(summary_title) - 2) // 2 + (width - len(summary_title) - 2) % 2) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        
        # Format summary lines to fit width
        files_str = f"📁  Files Processed: {format_number(len(files))}"
        lines_str = f"📄  Total Lines: {format_number(total_lines)}"
        msgs_str = f"💬  Messages w/ Usage: {format_number(total_messages)}"
        
        print(f"║  {files_str:<{width - 4}}  ║")
        print(f"║  {lines_str:<{width - 4}}  ║")
        print(f"║  {msgs_str:<{width - 4}}  ║")
        print("╚" + "═" * (width - 2) + "╝")
        
        # Model breakdown
        sorted_models = sorted(grand_total.items(), key=lambda x: -x[1]['total'])
        
        print()
        print("📊" + "═" * (width - 4) + "📊")
        model_title = "🤖 TOKEN USAGE BY MODEL 🤖"
        print("║" + " " * ((width - len(model_title) - 2) // 2) + model_title + " " * ((width - len(model_title) - 2) // 2 + (width - len(model_title) - 2) % 2) + "║")
        print("📊" + "═" * (width - 4) + "📊")
        
        for rank, (model, counts) in enumerate(sorted_models, 1):
            emoji = get_provider_emoji(model)
            total_all = sum(m['total'] for m in grand_total.values())
            
            print()
            print("┌" + "─" * (width - 2) + "┐")
            
            # Model header - truncate if needed
            model_display = f"#{rank:<2} {emoji}  {model}"
            if len(model_display) > width - 4:
                model_display = model_display[:width - 7] + "..."
            print(f"│ {model_display:<{width - 4}} │")
            print("├" + "─" * (width - 2) + "┤")
            
            # Token lines
            # Calculate column widths based on terminal width
            num_width = 15  # space for formatted number
            pct_width = 6   # space for percentage
            
            # Input
            pct = (counts['input'] / total_all * 100) if total_all > 0 else 0
            line = f"  📥  Input:    {format_number(counts['input']):>{num_width}}  ({format_tokens(counts['input'])})"
            if len(line) + pct_width + 4 < width:
                line += f"  {pct:>5.1f}%"
            print(f"│{line:<{width - 2}}│")
            
            # Output
            pct = (counts['output'] / total_all * 100) if total_all > 0 else 0
            line = f"  📤  Output:   {format_number(counts['output']):>{num_width}}  ({format_tokens(counts['output'])})"
            if len(line) + pct_width + 4 < width:
                line += f"  {pct:>5.1f}%"
            print(f"│{line:<{width - 2}}│")
            
            # Cache Read
            if counts['cache_read'] > 0:
                pct = (counts['cache_read'] / total_all * 100) if total_all > 0 else 0
                line = f"  💾  Cache R:  {format_number(counts['cache_read']):>{num_width}}  ({format_tokens(counts['cache_read'])})"
                if len(line) + pct_width + 4 < width:
                    line += f"  {pct:>5.1f}%"
                print(f"│{line:<{width - 2}}│")
            
            # Cache Write
            if counts['cache_write'] > 0:
                pct = (counts['cache_write'] / total_all * 100) if total_all > 0 else 0
                line = f"  💿  Cache W:  {format_number(counts['cache_write']):>{num_width}}  ({format_tokens(counts['cache_write'])})"
                if len(line) + pct_width + 4 < width:
                    line += f"  {pct:>5.1f}%"
                print(f"│{line:<{width - 2}}│")
            
            print("├" + "─" * (width - 2) + "┤")
            total_line = f"  🔥  TOTAL:    {format_number(counts['total']):>{num_width}}  ({format_tokens(counts['total'])})"
            print(f"│{total_line:<{width - 2}}│")
            print("└" + "─" * (width - 2) + "┘")
        
        # Grand totals
        print()
        print("💰" + "═" * (width - 4) + "💰")
        grand_title = "🏆 GRAND TOTALS 🏆"
        print("║" + " " * ((width - len(grand_title) - 2) // 2) + grand_title + " " * ((width - len(grand_title) - 2) // 2 + (width - len(grand_title) - 2) % 2) + "║")
        print("💰" + "═" * (width - 4) + "💰")
        
        total_in = sum(m['input'] for m in grand_total.values())
        total_out = sum(m['output'] for m in grand_total.values())
        total_cache_r = sum(m['cache_read'] for m in grand_total.values())
        total_cache_w = sum(m['cache_write'] for m in grand_total.values())
        total_all = sum(m['total'] for m in grand_total.values())
        
        num_width = 15
        
        line = f"│  📥  TOTAL INPUT       {format_number(total_in):>{num_width}}  ({format_tokens(total_in)})"
        print(f"{line:<{width - 1}}│")
        
        line = f"│  📤  TOTAL OUTPUT      {format_number(total_out):>{num_width}}  ({format_tokens(total_out)})"
        print(f"{line:<{width - 1}}│")
        
        if total_cache_r > 0:
            line = f"│  💾  TOTAL CACHE READ  {format_number(total_cache_r):>{num_width}}  ({format_tokens(total_cache_r)})"
            print(f"{line:<{width - 1}}│")
        
        if total_cache_w > 0:
            line = f"│  💿  TOTAL CACHE WRITE {format_number(total_cache_w):>{num_width}}  ({format_tokens(total_cache_w)})"
            print(f"{line:<{width - 1}}│")
        
        print("├" + "─" * (width - 2) + "┤")
        line = f"│  🔥  GRAND TOTAL       {format_number(total_all):>{num_width}}  ({format_tokens(total_all)})"
        print(f"{line:<{width - 1}}│")
        print("└" + "─" * (width - 2) + "┘")
        
        # Cost estimation tip
        print()
        print("💡" + "─" * (width - 4) + "💡")
        
        # Word wrap the tip text
        tip_lines = [
            "💰 Cost Estimation Tip:",
            "Use serper-search to find current API pricing:",
            "'Anthropic Claude API pricing per token 2025'",
            "'OpenAI o1 API pricing per million tokens'",
            "Then: tokens × price_per_token = estimated cost"
        ]
        
        for tip in tip_lines:
            print(f"│  {tip:<{width - 4}}│")
        
        print("💡" + "─" * (width - 4) + "💡")


if __name__ == '__main__':
    main()
