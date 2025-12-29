int[2][2] x = {{1,2},{3,4}};
string y = "test1";
print(y);

func fun(int[2][2] x, string y){
    print(y);
    y = "test3";

    print(x[0][0]);

    func fun2(string y){
        print(y);
        y = "test4";
        print(y);
    }
    fun2(y);
    print(y);
    x[0][0] = 10;
    print(x[0][0]);
}
y = "test2";
print(y);

fun(x, y);

print(x[0][0]);
print(y);