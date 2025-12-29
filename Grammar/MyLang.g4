
grammar MyLang;

//////////////////////////////
// Program i bloki
//////////////////////////////

// Cały program musi być umieszczony w jednym bloku
program
    : importStmt* statement* EOF
    ;

// Może swap na statement w program
globalDecl
    : varDecl ';'
    | funcDecl
    | structDecl
    | classDecl
    ;

importStmt
    : 'import' STRING ';'
    ;

// Blok – ciąg instrukcji otoczonych klamrami
block
    : '{' statement* '}'
    ;

//////////////////////////////
// Instrukcje
//////////////////////////////

statement
    : varDecl ';'                   // deklaracja zmiennej (statyczna lub dynamiczna)
    | assignment ';'               // przypisanie
    | printStmt ';'                 // wywołanie print
    | readStmt ';'                  // wywołanie read
    | ifStmt                        // instrukcja warunkowa
    | whileStmt                     // pętla while
    | forStmt                       // pętla for
    | funcDecl                      // definicja funkcji
    | structDecl                    // definicja struktury
    | classDecl                     // definicja klasy (opcjonalne dziedziczenie)
    | returnStmt
    | yieldStmt
    | expr ';'                  // wyrażenie jako instrukcja
    ;

//////////////////////////////
// Deklaracje zmiennych
//////////////////////////////

// Zmienna może być zadeklarowana przez jawny typ lub dynamicznie (słowo "var")

varDecl
    : ( static='static' )? (advancedType | var='var') (ID ('=' initializer)?)
    ;

// Proste przypisanie BEZ średnika (używane tylko w pętlach)
assignment
    : assignable '=' initializer
    ;

assignable
    : ID references?
    ;

references
    : reference+
    ;

reference
    : (indexing | '.' ID)
    ;

initializer
    : expr
    | arrayInitializer
    ;

// Nowy sposób na zagnieżdżone inicjalizatory
arrayInitializer
    : '{' (arrayElement (',' arrayElement)*)? '}'
    ;

// arrayElement może być kolejnym inicjalizatorem lub zwykłym wyrażeniem
arrayElement
    : arrayInitializer
    | expr
    ;

printStmt
    : 'print' '(' expr ')'
    ;

readStmt
    : 'read' '(' ID ')'
    ;

//////////////////////////////
// Instrukcje sterujące
//////////////////////////////

ifStmt
    : 'if' '(' expr ')' block ( else = 'else' block)?
    ;

whileStmt
    : 'while' '(' expr ')' block
    ;

forStmt
    : foreach
    | simpleFor
    ;

simpleFor
    : 'for' '(' (decl_assignmentLabel=assignment | decl_vardeclLabel=varDecl)? ';' conditionLabel=expr? ';' (operation_assLabel=assignment | operation_expressLabel=expr)? ')' blockLabel=block
    ;

foreach
    : 'for' '(' ID 'in' expr ')' block
    ;

//////////////////////////////
// Funkcje i generatory
//////////////////////////////

// Definicja funkcji
funcDecl
    : ( static = 'static' )? (func='func' | generator='generator') ID '(' paramList? ')' block
    ;

paramList
    : param (',' param)*
    ;

param
    : advancedType ID
    ;

//////////////////////////////
// Struktury i klasy
//////////////////////////////

// Definicja struktury – tylko pola (zmienne)
structDecl
    : 'struct' ID '{' structMemberList '}'
    ;

structMemberList
    : structMember*
    ;

structMember
    : advancedType ID ';'
    ;

// Definicja klasy – pola i funkcje; opcjonalne dziedziczenie
classDecl
    : 'class' ID '{' 
        fieldDecl* 
        constructorDecl*
        funcDecl*
     '}'
    ;

fieldDecl
    : advancedType ID ( '=' expr )? ';'
    ;


classMemberList
    : classMember*
    ;

classMember
    : varDecl ';'
    | funcDecl
    | constructorDecl          // ADDED constructor
    ;

constructorDecl
    : 'constructor' '(' paramList? ')' block
    ;

//////////////////////////////
// Wyrażenia (operator precedence)
//////////////////////////////

expr
    : orExpr
    ;

orExpr
    : orExpr 'OR' andExpr
    | andExpr
    ;

andExpr
    : andExpr 'AND' xorExpr
    | xorExpr
    ;

xorExpr
    : xorExpr 'XOR' eqExpr
    | eqExpr
    ;

// ADDED – eqExpr obsługuje '==' i '!='
eqExpr
    : eqExpr (equals='==' | notEquals='!=') relExpr
    | relExpr
    ;

// ADDED – relExpr obsługuje '<', '>', '<=', '>='
relExpr
    : relExpr (less='<' | more='>' | lessEqual='<=' | moreEqual='>=') addExpr
    | addExpr
    ;

addExpr
    : addExpr (add='+'|sub='-') mulExpr
    | mulExpr
    ;

mulExpr
    : mulExpr (multiply='*'|divide='/') unaryExpr
    | unaryExpr
    ;

castExpr
    : '(' primitiveType ')' unaryExpr
    ;

unaryExpr
    : castExpr
    | 'NEG' unaryExpr
    | primaryExpr
    ;

primaryExpr
    : '(' expr ')' // nawiasy w equation np. x*(z+y)
    | newObjectExpr    // tworzenie nowego obiektu
    | funcCall
    | literal
    | objectReference
    ;

newObjectExpr
    : 'new' ID '(' argumentList? ')'
    ;

accessOp
    : indexing              // np. a[0]
    | '.' ID                // np. obiekt.pole
    ;

funcCall
    : objectReference '(' argumentList? ')'
    ;

objectReference
    : ID references?
    ;

argumentList
    : expr (',' expr)*
    ;

indexing
    : indexRange
    | index            
    ;

indexRange
    : '[' leftExpr=expr? ':' rightExpr=expr? ']' 
    ;

index
    : '[' expr ']' // zezwala na a[i+1]
    ;

literal
    : INT
    | FLOAT
    | BOOL
    | STRING
    ;

returnStmt
    : 'return' expr? ';'
    ;

yieldStmt
    : 'yield' expr? ';'
    ;

//////////////////////////////
// Typy
//////////////////////////////

// Typy dla deklaracji zmiennych, tablic i macierzy
advancedType
    : primitiveType
    | multiArrayType
    | generatorType
    | ID 
    ;

generatorType
    : 'generator' '<' primitiveType '>'
    ;

primitiveType
    : 'int'
    | 'float'
    | 'double'
    | 'bool'
    | 'string'
    ;

// Tablica jednowymiarowa – element musi być typem podstawowym
multiArrayType
    : primitiveType dimensions
    ;

dimensions
    : dimension+
    ;

dimension
    : '[' INT ']'
    ;

//////////////////////////////
// Tokeny
//////////////////////////////

BOOL    : 'True'|'true'|'False'|'false' ;
INT     : '-'? [0-9]+ ;
FLOAT   : '-'? [0-9]+ '.' [0-9]+ ;
STRING  : '"' (~["\r\n])* '"' ;
ID      : [a-zA-Z_][a-zA-Z_0-9]* ;
COMMENT : '//' ~[\r\n]* -> skip ;
WS      : [ \t\r\n]+ -> skip ;
