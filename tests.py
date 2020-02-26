import unittest

import ucsautomation


class MovingVlans(unittest.TestCase):

    def test_move_vlan666_from_null_to_group(self):
        vlan = "666"
        target_name = "ACI-CORP"
        c = ucsautomation.Controller.load()
        c.connect()
        vlans = c.move_vlan(vlan, target_name=target_name)
        vlan_names = [vlan.name for vlan in vlans]
        c.commit()
        pooled_vlans = c.get_objects_state_from_class_id('fabricPooledVlan')
        for pooled_vlan in pooled_vlans:
            if pooled_vlan.name in vlan_names:
                parent_mo = c.handler.query_dn(pooled_vlan._ManagedObject__parent_dn)
                print(f"Are these the same? target={target_name} and final={parent_mo.name}")
                self.assertEqual(target_name, parent_mo.name)

    def test_move_vlan666_from_group_to_null(self):
        vlan = "666"
        source_name = "ACI-CORP"
        c = ucsautomation.Controller.load()
        c.connect()
        vlans = c.move_vlan(vlan, source_name=source_name)
        vlan_names = [vlan.name for vlan in vlans]
        c.commit()
        pooled_vlans = c.get_objects_state_from_class_id('fabricPooledVlan')
        for pooled_vlan in pooled_vlans:
            if pooled_vlan.name in vlan_names:
                self.assertEqual(True, False, msg=f"vlan {vlan_names} is still a pooled vlan")


if __name__ == '__main__':
    unittest.main()
