..
      Copyright 2019 IBM
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.
      
More Than One Network
*********************

In the current Neutron z/VM agent implementation, physical network names are
used as vswitch names. There is no limitation on the number or the order of
physical networks, so in the Neutron ML2 plugin configuration file
(/etc/neutron/plugins/ml2/ml2_conf.ini), you could have::

    flat_networks = vsw3,vsw3
    network_vlan_ranges = vsw4:1:4094,vsw5:1:4094

And in the Neutron z/VM agent configuration file (/etc/neutron/plugins/zvm/neutron_zvm_plugin.ini), you could have::

    [AGENT] 
    cloud_connector_url = http:// 10.0.0.3:8080/
    [vsw2]
    # OSA2 uses RDEV A2
    rdev_list=a2
    [vsw3]
    # OSA3 uses RDEV A3
    rdev_list=a3
    [vsw4]
    # OSA4 uses RDEV A4
    rdev_list=a4
    [vsw5]
    # OSA5 uses RDEV A5
    rdev_list=a5

The Neutron z/VM agent will create vswitches named vsw1, vsw2, vsw3 and vsw4.
vsw2 and vsw3 will be a VLAN UNAWARE vswitch, while vsw4 and vsw5 will
be VLAN AWARE.

.. note::

    Each of the switches needs at least one OSA defined. The OSA card needs to be connected to the
    trunk port if the VLAN is enabled. The related rdev_list should be updated to list one of the OSAs.

With the vswitches, more networks can be defined, as follows.

* Create the flat networks for physical network vsw2 and vsw3::

    openstack network create --shared --provider-network_type flat --provider-physical_network vsw2 flat2
    
    openstack network create --shared --provider-network_type flat --provider-physical_network vsw3 flat3

* Create the appropriate subnet for the flat networks::

    Openstack subnet create --allocation-pool start=1.2.3.5,end=1.2.3.254 --network flat2 --subnet-range 1.2.3.0/24 --gateway 1.2.3.1 flat2-sub 

    Openstack subnet create --allocation-pool start=2.2.3.5,end=2.2.3.254 --network flat3 --subnet-range 2.2.3.0/24 --gateway 2.2.3.1 flat3-sub
 
* Create the vlan network for physical network vsw4 and vsw5::

    openstack network create --shared --provider-network_type vlan --provider-physical_network vsw4 --provider-segment 104 vlan4

    openstack network create --shared --provider-network_type vlan --provider-physical_network vsw5 --provider-segment 105 vlan5

* Create the appropriate subnet for the vlan networks::
    
    Openstack subnet create --allocation-pool start=3.2.3.5,end=3.2.3.254 --network vlan4 --subnet-range 3.2.3.0/24 --gateway 3.2.3.1 vlan4-sub 

    Openstack subnet create --allocation-pool start=4.2.3.5,end=4.2.3.254 --network vlan5 --subnet-range 4.2.3.0/24 --gateway 4.2.3.1 vlan5-sub 

