import os
import re
import tokenize
import io
def strip_python_comments(source):
    io_obj = io.StringIO(source)
    out = ""
    last_lineno = -1
    last_col = 0
    try:
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                out += (" " * (start_col - last_col))
            if token_type == tokenize.COMMENT:
                pass
            else:
                out += token_string
            last_lineno = end_line
            last_col = end_col
    except tokenize.TokenError:
        return source
    return out
def strip_js_css_comments(source, is_js=False):
    if not is_js:
        return re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    else:
        source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
        source = re.sub(r'(?<!:)//.*', '', source)
        return source
def strip_html_comments(source):
    return re.sub(r'<!--.*?-->', '', source, flags=re.DOTALL)
def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.py':
        new_source = strip_python_comments(source)
    elif ext == '.css':
        new_source = strip_js_css_comments(source, is_js=False)
    elif ext == '.js':
        new_source = strip_js_css_comments(source, is_js=True)
    elif ext == '.html':
        new_source = strip_html_comments(source)
    else:
        return
    lines = [line for line in new_source.split('\n') if line.strip() != '']
    new_source = '\n'.join(lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_source)
def main():
    root_dir = r"d:\claude_codes\gym-tracker"
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '.venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
            continue
        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.py', '.js', '.css', '.html']:
                filepath = os.path.join(dirpath, file)
                print(f"Processing {filepath}")
                process_file(filepath)
if __name__ == "__main__":
    main()