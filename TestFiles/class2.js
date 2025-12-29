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

func funny(Point papa){
    print(papa.x);

    papa.x = 23;

    print(papa.x);
}

funny(p);