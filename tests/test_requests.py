import unittest
from narrative.core import World
from test_world_v2 import rich


class RequestTests(unittest.TestCase):
    def test_request_reaches_decision_maker_and_allocation_fulfills_it(self):
        w=World(rich())
        event=w.act({'actor':'b','kind':'request','org':'guild','resource':'food','amount':2})
        self.assertEqual(w.view('a')['requests'][0]['remaining'],2)
        result=w.act({'actor':'a','kind':'allocate','org':'guild','resource':'food','amount':2,'target':'b'})
        self.assertEqual(w.state['requests'][0]['status'],'fulfilled')
        self.assertIn(event['id'],result['dependencies'])
        self.assertEqual(w.state['organizations']['guild']['resources']['food'],1)

    def test_middle_quantity_is_available(self):
        w=World(rich())
        self.assertTrue(any(a['kind']=='allocate' and a['amount']==2 for a in w.actions('a')))

    def test_request_does_not_leak_to_outsider(self):
        w=World(rich())
        w.act({'actor':'b','kind':'request','org':'guild','resource':'food','amount':2})
        self.assertEqual(w.view('c')['requests'],[])
