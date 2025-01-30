class TestVar:
    # def __init__(self, disable):
    def __init__(self):
        # self.disable = disable
        self.disable = False

class TestVar2:
    # def __init__(self):
        # self.disable = False
    def mreow(self):
        # self.view = TestVar(self.disable)
        self.view = TestVar()
        print (self.view.disable)

a = TestVar2()
a.mreow()
