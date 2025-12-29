class Point {
    int x;
    int y;

    constructor(int ax, int ay) {
        self.x = ax;
        self.y = ay;
    }

    func sum() {
        int k = self.x + self.y;
        print(k);
        return k;
    }

    func mult(int n){
        int mult_res = self.x * n;

        self.y = mult_res;

        return mult_res;
    }
}

Point p = new Point(3, 4);
print(p.x);
int suma = p.sum();

print(suma + 3);

int multi_result = p.mult(2);
print(multi_result);
print(p.y);

print("-----------");

func funny(Point papa){
    print(papa.x);

    papa.x = 23;

    print(papa.x);
}


class Point2 {
    int x;
    int y;

    constructor(int ax, int ay) {
        self.x = ax;
        self.y = ay;
    }

    func sum() {
        int k = self.x + self.y;
        print(k);
        return k;
    }

    func mult(int n){
        int mult_res = self.x * n;

        self.y = mult_res;

        return mult_res;
    }
}

Point2 p2 = new Point2(1, 2);
print(p2.x);
int suma2 = p2.sum();

print(suma2 + 3);

int multi_result2 = p2.mult(4);
print(multi_result2);
print(p.y);

print(p.sum());

print("=======================");

funny(p);
print(p.x);

Point2 p3 = p2;

print("-=-=-=-=-=-=-=-=-");

print(p3.x);

p2.x = 124;

print(p3.x);