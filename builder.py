import os
import subprocess
import sys

def build_grammar(grammar_path):
    output_folder = "LexerParser"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cmd = f'java -jar Grammar/antlr-4.13.2-complete.jar -Dlanguage=Python3 -o {output_folder} {grammar_path} -visitor'
    print("[1...] Building grammar:", cmd)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Błąd podczas budowania gramatyki")
        sys.exit(1)
    print("[1+++] Gramatyka zbudowana poprawnie, wyniki w folderze:", output_folder)

def run_main(source_path):
    out_folder = "Output"
    main_script = "Main/main.py"  # Ścieżka do main.py w folderze Main
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
    output_ll = os.path.join(out_folder, "program.ll")  # Zapisz wynikowy plik .ll do Output

    cmd = ["python", main_script, source_path, output_ll]
    print("[2...] Running main:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[2---] Błąd podczas uruchamiania main.py")
        sys.exit(1)
    print("[2+++] main.py uruchomiony poprawnie, LLVM IR zapisany w folderze:", out_folder)

def run_clang():
    out_folder = "Output"
    ll_file = os.path.join(out_folder, "program.ll")
    exe_file = os.path.join(out_folder, "program.exe")
    cmd = ["clang ", ll_file, "-o", exe_file, "-llegacy_stdio_definitions"]
    print("[3...] Running clang:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Błąd podczas kompilacji clangiem")
        sys.exit(1)
    print("[3+++] Clang zakończył działanie poprawnie, wygenerowany program:", exe_file)

if __name__ == "__main__":
    grammar_file = "Grammar/MyLang.g4"
    source_file = sys.argv[1]
    
    build_grammar(grammar_file)
    run_main(source_file)
    run_clang()
    
    result = subprocess.run("Output/program.exe")
    
