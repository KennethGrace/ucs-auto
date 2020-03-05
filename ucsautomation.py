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
import os
import argparse
from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.mometa.fabric.FabricPooledVlan import FabricPooledVlan
from ucsmsdk.mometa.fabric.FabricVlan import FabricVlan
from ucsmsdk.mometa.fabric.FabricEthVlanPc import FabricEthVlanPc


class Controller:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.handler = None
        self.change_log = []
        self.state = {}
        print("Local State Data Created")

    @classmethod
    def load(cls, filename="config.yaml"):
        import yaml
        with open(filename, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(config['host'], config['username'], config['password'])

    def connect(self) -> UcsHandle:
        self.handler = UcsHandle(self.host, self.username, self.password)
        self.handler.login()
        return self.handler

    def commit(self):
        if len(self.change_log) > 0:
            print("COMMIT LOG:")
            for line in self.change_log:
                print(line)
            if input('Confirm Commit (y,n)? ') == 'y':
                self.handler.commit()
                print("Remote State Changes Committed")
                self.state = {}
                self.change_log = []
                print("Local State Data Destroyed")
        else:
            print("No Changes To Commit, skipping...")

    def get_objects_state_from_class_id(self, class_id):
        if class_id not in self.state:
            self.state[class_id] = self.handler.query_classid(class_id)
            print(f"Local State Data Updated with \"{class_id}\"")
        return self.state[class_id]

    def move_vlan(self, vlan_id, source_name=None, target_name=None):
        """
        move_vlan will take a series of vlans bound to a specific id, remove them from old local and add them to a
        new local. When no group names are passed, null is interpreted as an unbound Vlan. When an invalid group name
        is passed this function fails, raising an exception

        :param vlan_id: The VLAN ID to migrate
        :param source_name: The source Vlan Group (null if Not Bound)
        :param target_name: The target Vlan Group (null if Not Bound)
        :return: target_vlans: List: A list of the vlan managed objects which were moved.
        """
        vlans = self.get_objects_state_from_class_id('fabricVlan')
        target_vlans = [vlan for vlan in vlans if vlan.id == vlan_id]
        # Oh, shit boiiiii, we found it.
        target_vlan_names = [vlan.name for vlan in vlans]
        vlan_groups = self.get_objects_state_from_class_id('fabricNetGroup')
        source, target = None, None
        if source_name:
            source = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == source_name)
        if target_name:
            target = next(vlanGroup for vlanGroup in vlan_groups if vlanGroup.name == target_name)
        # If there is a source vlan group, then we want to strip off all pooled vlans from that vlan group that match
        # the vlan_id, but if no source vlan group was defined, we want to remove port-channels which are bound under
        # this vlan to insure forwarding only occurs on port-channels bound to the vlan group we are migrating too.
        # TODO: Identify why this script grabs so many vlans beyond what it should be grabbing. The error is likely in
        #  this function.
        if source:
            group_vlans = self.handler.query_dn(source.dn, hierarchy=True)
            for groupVlan in group_vlans:
                if groupVlan.name in target_vlan_names:
                    self.handler.remove_mo(groupVlan)
                    self.change_log.append(f"remove({groupVlan.dn})")
        else:
            for vlan in target_vlans:
                children = self.handler.query_dn(vlan.dn, hierarchy=True)
                for child in children:
                    # pop off every port-channel which is a child of this vlan
                    if isinstance(child, FabricEthVlanPc):
                        self.handler.remove_mo(child)
                        self.change_log.append(f"remove({child.dn})")
        # If there is a target vlan group defined we want to create a fabricPooledVlan child object of that vlan group
        # for every vlan which matches the vlan_id, otherwise, we will leave the vlan unbound.
        if target:
            for targetVlan in target_vlans:
                tmp = FabricPooledVlan(parent_mo_or_dn=target, name=targetVlan.name)
                self.handler.add_mo(tmp, modify_present=True)
                self.change_log.append(f"create({tmp.dn})")
        self.change_log.append(f"move_vlan({vlan_id},source_name={source_name},target_name={target_name})")
        return target_vlans

    def show_vlans(self, vlan_id):
        if 'vlan' not in self.state:
            self.state['vlan'] = self.handler.query_classid('fabricVlan')
        target_vlans = [vlan for vlan in self.state['vlan'] if vlan.id == vlan_id]
        for vlan in target_vlans:
            print(vlan)


def main(*args) -> int:
    parser = argparse.ArgumentParser(description="A Simple UCS Automation Script")
    subparsers = parser.add_subparsers(help="Type of operation to perform")
    sysparser = subparsers.add_parser('system', help="Perform a operation on the system")
    vlanparser = subparsers.add_parser('vlan', help="Perform a operation on vlans")
    vlanparser.add_argument('vlan_id', type=str, help="VLAN ID to migrate")
    vlanparser.add_argument('--source', dest='source', default=None, type=str, help="A source VLAN Group")
    vlanparser.add_argument('--target', dest='target', default=None, type=str, help="A target VLAN Group")
    params = parser.parse_args(args)
    controller = Controller.load()
    controller.connect()
    controller.move_vlan(params.vlan_id, source_name=params.source if params.source else None,
                         target_name=params.target if params.target else None)
    controller.commit()
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    code = main(*a)
    sys.exit(code)
