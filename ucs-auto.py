#!/usr/bin/env python
#
# Vlan Migration
# Use this tool to move a vlan from one vlan group to another on a UCS
# Manager instance. You will need to install the ucsmsdk via pip.
#
# 2018 Dyntek Services Inc.
# Kenneth J. Grace <kenneth.grace@dyntek.com>
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import sys
from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.mometa.fabric.FabricPooledVlan import FabricPooledVlan
from ucsmsdk.mometa.fabric.FabricVlan import FabricVlan


class Controller:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.handler = None
        self.change_log = []

    @classmethod
    def load(cls, filename="config.yaml"):
        import yaml
        with open(filename, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        print(config)
        return cls(config['host'], config['username'], config['password'])

    def connect(self) -> UcsHandle:
        self.handler = UcsHandle(self.host, self.username, self.password)
        self.handler.login()
        return self.handler

    def commit(self):
        if len(self.change_log) > 0:
            for line in self.change_log:
                print(line)
            if input('Confirm Commit (y,n)? ') == 'y':
                self.handler.commit()
        else:
            print("No Changes To Commit, skipping")

    def move_vlan(self, vlan_id, source=None, target=None):
        """
        move_vlan will take a series of vlans bound to a specific id, remove them from and old local and add them to a
        new local. When no group names are passed, null is interpreted as an unbound Vlan.

        :param vlan_id: The VLAN ID to migrate
        :param source: The source Vlan Group (null if Not Bound)
        :param target: The target Vlan Group (null if Not Bound)
        :return:
        """
        vlans = self.handler.query_classid('fabricVlan')
        target_vlans = [vlan.name for vlan in vlans if vlan.id == vlan_id]
        vlan_groups = self.handler.query_classid('fabricNetGroup')
        if source:
            old_vlan_group = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == source)
        if target:
            new_vlan_group = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == target)
        self.change_log.append(f"move_vlan({source},{target},{vlan_id})")

    def show_vlan(self, vlan_id):
        vlans = self.handler.query_classid('fabricVlan')
        target_vlans = [vlan for vlan in vlans if vlan.id == vlan_id]
        for vlan in target_vlans:
            print(vlan)

    def show_pooled_vlans(self):
        vlans = self.handler.query_classid('fabricPooledVlan')
        for vlan in vlans:
            print(vlan)

    def show_vlan_groups(self):
        vlan_groups = self.handler.query_classid('fabricNetGroup')
        for group in vlan_groups:
            print(group)


def main() -> int:
    controller = Controller.load()
    controller.connect()
    controller.show_vlan("666")
    controller.show_vlan_groups()
    controller.show_pooled_vlans()
    # vlans = handle.query_classid('fabricVlan')
    # target_vlans = [vlan.name for vlan in vlans if vlan.id == vlan_id]
    # vlan_groups = handle.query_classid('fabricNetGroup')
    # old_vlan_group = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == old_group)
    # new_vlan_group = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == new_group)
    # group_vlans = handle.query_dn(old_vlan_group.dn, hierarchy=True)
    # for groupVlan in group_vlans:
    #     if groupVlan.name in target_vlans:
    #         handle.remove_mo(groupVlan)
    # for targetVlan in target_vlans:
    #     tmp = FabricPooledVlan(parent_mo_or_dn=new_vlan_group, name=targetVlan)
    #     handle.add_mo(tmp, modify_present=True)
    # handle.commit()
    controller.commit()
    return 0


if __name__ == '__main__':
    args = sys.argv[1:]
    code = main()
    sys.exit(code)
