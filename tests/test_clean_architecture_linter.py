import unittest
from governance.clean_architecture_linter import check_source


OK_SNIPPET = """
def short():
    return 1
"""

TOO_LONG_SNIPPET = """
def too_long():
    a=1
    b=2
    c=3
    d=4
    e=5
    f=6
    g=7
    h=8
    i=9
    j=10
    k=11
    l=12
    m=13
    n=14
    o=15
    p=16
    q=17
    r=18
    s=19
    t=20
    u=21
    return a+b+c
"""


class TestCALinter(unittest.TestCase):
    def test_ok(self):
        v = check_source(OK_SNIPPET, filename="MEM", max_len=20)
        self.assertEqual(v, [])

    def test_too_long(self):
        v = check_source(TOO_LONG_SNIPPET, filename="MEM", max_len=20)
        self.assertTrue(any(vi.rule == "FUNC_LEN" for vi in v))


if __name__ == "__main__":
    unittest.main()

