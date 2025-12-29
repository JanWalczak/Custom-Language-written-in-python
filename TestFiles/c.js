string[2][2] h;

h[0][0] = "test";
h[0][1] = "test2";

string k;

k = h[0][1];
print(k);

int[2][2][2] y = 
{
    {
        {1,2}, {3,4}
    },
    {
        {5,6}, {7,8}
    }
};

print(y[0][1][0]);

y[0] = {{11,12},{13,14}};

print(y[0][0][0]);
print(y[0][0][1]);
print(y[0][1][0]);
print(y[0][1][1]);

int[2][2] a = y[1];

y[1][0][1] = 12313;

print(a[0][1]);


string[2][2][2] x = 
{
    {
        {"a","b"}, {"c","d"}
    },
    {
        {"e","f"}, {"g","h"}
    }
};

print(x[0][1][0]);

x[0] = {{"s","i"},{"e","m"}};

print(x[0][0][0]);
print(x[0][0][1]);
print(x[0][1][0]);
print(x[0][1][1]);

string[2][2] b = x[0];

print(b[0][1]);

bool[2][2][2] z = 
{
    {
        {True,True}, {false,false}
    },
    {
        {false,false}, {True,True}
    }
};

print(z[0][1][0]);

z[0] = {{false,true},{false,false}};

print(z[0][0][0]);
print(z[0][0][1]);
print(z[0][1][0]);
print(z[0][1][1]);

bool[2][2] c = z[0];

print(c[0][1]);

string[2][2] g;

g = x[:][0][:];

print(g[0][0]);
print(g[0][1]);
print(g[1][0]);
print(g[1][1]);

