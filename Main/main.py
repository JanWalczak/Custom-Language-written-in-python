# main.py
import sys
import os
from graphviz import Source
from antlr4.tree.Trees import Trees
from antlr4 import FileStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.Errors         import ParseCancellationException
# Zakładamy, że parser i lexer są wygenerowane do folderu lexpars
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LexerParser.MyLangLexer import MyLangLexer
from LexerParser.MyLangParser import MyLangParser
from LLVMActions import LLVMActions

class CollectingListener(ErrorListener):
    """Zbiera komunikaty z lexera i parsera."""
    def __init__(self):
        super().__init__()
        self.messages = []                  # (line, col, msg)

    def syntaxError(self, recognizer, offendingSymbol, line, col, msg, e):
        self.messages.append((line, col, msg))

def generate_dot(tree, rule_names):
    dot_lines = ["digraph AST {"]
    counter = 0

    def traverse(node, parent_id=None):
        nonlocal counter
        node_id = counter
        counter += 1
        # Pobierz tekst węzła i escapuj cudzysłowy
        label = Trees.getNodeText(node, rule_names)
        label = label.replace('"', '\\"')  # Escapowanie cudzysłowów
        dot_lines.append(f'  node{node_id} [label="{label}"];')
        if parent_id is not None:
            dot_lines.append(f'  node{parent_id} -> node{node_id};')
        if hasattr(node, "children") and node.children:
            for child in node.children:
                traverse(child, node_id)

    traverse(tree)
    dot_lines.append("}")
    return "\n".join(dot_lines)

def abort(errors):
    print("[!] Compilation abborted:\n")
    for ln, col, msg in errors:
        print(f"   line {ln}:{col}  {msg}")
    sys.exit(1)

def main():
    source_file = sys.argv[1]
    try:
        input_stream = FileStream(source_file, encoding="utf-8")
    except FileNotFoundError:
        print(f"[1--.] Nie znaleziono pliku: {source_file}")
        sys.exit(1)
    lexer = MyLangLexer(input_stream)
    lex_err = CollectingListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lex_err)

    tokens = CommonTokenStream(lexer)
    parser = MyLangParser(tokens)
    parse_err = CollectingListener()
    parser.removeErrorListeners()
    parser.addErrorListener(parse_err)

    try:
        tree = parser.program() # zakładamy, że główna reguła to 'program'
    except ParseCancellationException:
        tree = None

    # Sprawdzenie błędów leksykalnych i składniowych
    if lex_err.messages or parse_err.messages or tree is None:
        abort(lex_err.messages + parse_err.messages)

    dot_text = generate_dot(tree, parser.ruleNames)

    # Wyświetl jako graf
    graph = Source(dot_text, filename="Output/Source", format="pdf")
    graph.view()  # otwiera okno z obrazkiem lub pokazuje inline w Jupyter

    actions = LLVMActions()
    llvm_ir = actions.visit(tree)
    
    out_dir = "Output"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    output_ll = os.path.join(out_dir, "program.ll")
    print(llvm_ir)
    if llvm_ir:
        with open(output_ll, "w", encoding="utf-8") as f:
            f.write(llvm_ir)
    else:
        print("[2--.] Nie wygenerowano kodu LLVM_IR")
        sys.exit(1)


if __name__ == "__main__":
    main()
