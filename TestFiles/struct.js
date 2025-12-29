struct a{
    int x;
    string y;
    int[3] z; 
}

a struktura = new a();
a struktura2 = new a();

struktura.x = 5;
struktura.y = "siema";
struktura.z[:2] = {1, 2};

print(struktura.x);

struktura2 = struktura;

print(struktura2.z[1]);
struktura.x = 145;
print(struktura.x);
print(struktura2.x);
print(struktura.y);
print(struktura2.y);