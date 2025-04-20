from multiproc.multiproc_class import MultiProcCls

class Test:
    def __init__(self, attr3):
        self.attr1 = 1
        self.attr2 = "hi"
        self.attr3 = attr3

    def test1(self):
        print(self.attr1)
    def test2(self):
        print(self.attr2)
    def test3(self):
        print(self.attr3)

if __name__=="__main__":
    obj = MultiProcCls(Test, 4)
    obj.test3()
    print(obj.attr2)
    