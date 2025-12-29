struct a{
    int x;
    string y;
    int[3] z; 
}

int global_int = 123441244;

func fun(int k, a kreatura){
    print(kreatura.x);
    kreatura.x = 124;
    print(kreatura.x);
    print(k);

    print(global_int);
}

int z = 54;

a struktura = new a();
struktura.x = 5;

string xd = "siema";

a struktura2 = new a();

struktura2 = struktura;

print(struktura2.x);
print(struktura.x);
fun(z, struktura);
print(struktura.x);
