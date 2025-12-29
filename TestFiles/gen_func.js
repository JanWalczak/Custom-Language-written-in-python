print("Test case 1: Odd Numbers Generator");
generator oddNumbers(int start, int stop) {
    for (int i = start; i <= stop; i = i + 1) {
        if (i - (i / 2) * 2 == 1) {
            yield i;
        }
    }
}

generator<int> g1 = oddNumbers(3, 15);

while (g1.next()) {
    print(g1.current);
}
// Output: 3, 5, 7, 9, 11, 13, 15

print("Test case 2: Empty Range");
generator<int> g2 = oddNumbers(8, 7); 

while (g2.next()) {
    print(g2.current);
} 
// Output: (nothing)

print("Test case 3: Multiple Yields");
generator values() {
    yield 1;
    yield 2;
    yield 3;
}

generator<int> g3 = values();

while (g3.next()) {
    print(g3.current);
}
//Output: 1, 2, 3

print("Test case 4: Nested Generators");
generator doubleNumbers(int start, int stop) {
    for (int i = start; i <= stop; i = i + 1) {
        yield i * 2;
    }
}

generator<int> g4 = doubleNumbers(1, 5);

while (g4.next()) {
    int val = g4.current;
    print(val);
}
// Output: 2, 4, 6, 8, 10

print("Test case 5: Generator with a String Yield");
generator words() {
    yield "hello";
    yield "world";
    yield "from";
    yield "generator";
}

generator<string> g5 = words();

while (g5.next()) {
    print(g5.current);
}
// Output: hello, world, from, generator

print("Test case 6: Generator with Double Yield");
generator doubles() {
    yield 1.5;
    yield 3.1415;
    yield -2.71;
}

generator<double> g6 = doubles();

while (g6.next()) {
    print(g6.current);
}
// Output: 1.5, 3.1415, -2.71

print("Test case 7: Generator with Boolean Yield");
generator flags() {
    yield true;
    yield false;
    yield true;
}

generator<bool> g7 = flags();

while (g7.next()) {
    print(g7.current);
}
// Output: true, false, true

print("Test case 8: Generator with Conditional Yield");
generator skipWord(string skip) {
    string[4] items = {"apple", "banana", "cherry", "banana"};
    
    for (int i = 0; i < 4; i = i + 1) {
        if (items[i] != skip) {
            yield items[i];
        }
    }
}

generator<string> g8 = skipWord("banana");

while (g8.next()) {
    print(g8.current);
}
// Output: apple, cherry

print("Test case 9: Generator with Array Yield");
generator fromArray(int[4] arr) {
    for (int i = 0; i < 4; i = i + 1) {
        yield arr[i];
    }
}

int[4] arr = {10, 20, 30, 40};

generator<int> g9 = fromArray(arr);

while (g9.next()) {
    print(g9.current);
}
// Output: 10, 20, 30, 40
