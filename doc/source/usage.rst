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


Usage
************


To make use of the neutron z/VM driver, a z/VM cloud connector system is
required, and it should be installed on the target host which would be used to
create instances. Configuration of the z/VM cloud connector system is required
ahead of time.  And the URL of the z/VM cloud connector should be provided to
neutron z/VM drivers. 

Configuration File Options
==========================

This section describes the configuration settings related to the Neutron z/VM
driver. 

In file /etc/neutron/neutron.conf
---------------------------------

base_mac
^^^^^^^^
 **Optional**

 **Section:** DEFAULT

 **Value:** Base MAC address that is used to generate MAC for virtual
 interfaces specified as 6 pairs of hexadecimal digits separated by colons
 (for example, 02:00:00:EE:00:00).

 **Notes:**

 - The default value is: fa:16:3e:00:00:00
 - The first three pairs of hexadecimal digits should be the same as
   USERPREFIX in the VMLAN statement in the z/VM SYSTEM CONFIG file. You can
   modify the fourth pair to any range, as appropriate to your system. The
   final two pairs of hexadecimal digits for the MAC address should be 00 and
   will be replaced with generated values.

core_plugin
^^^^^^^^^^^
 **Required**

 **Section:** DEFAULT

 **Value:** ml2

 **Notes:** z/VM supports only the ML2 plugin. 
 
In file /etc/neutron/plugins/ml2/ml2_conf.ini
---------------------------------------------

flat_networks
^^^^^^^^^^^^^
 **Optional (with network_vlan_ranges)**

 **Section:** ml2_type_flat

 **Value:** Comma-separated list of z/VM vswitch names, with which flat
 networks can be created.

 **Notes:**

 - In the ML2 plugin configuration file, both the *flat_networks* property and
   the *network_vlan_ranges* property are optional. However, at least one of
   these properties must be specified. You can define a FLAT network with the
   *flat_networks* property, or you can define a VLAN aware network with the
   *network_vlan_ranges* property, or you can define both types of networks.
 - Specify either the vswitch names (for example, vsw2, vsw3) or use *
   to allow flat networks with arbitrary physical network names.

mechanism_drivers
^^^^^^^^^^^^^^^^^
 **Required**

 **Section:** ml2

 **Value:** zvm

 **Notes:** This property specifies the networking mechanism driver entry
 points to be loaded from the neutron.ml2.mechanism_drivers namespace.
 This value must be zvm.

network_vlan_ranges
^^^^^^^^^^^^^^^^^^^
 **Optional (with flat_networks)**

 **Section:** ml2_type_vlan

 **Value:** List of *vswitch[:vlan_min:vlan_max]* comma-separated values
 specifying z/VM vswitch names usable for VLAN provider and project networks,
 each followed by the range of VLAN tags on each vswitch available for
 allocation as project networks (for example, datanet1:1:4094,datanet3:1:4094).

 **Notes:**

 - In the ML2 plugin configuration file, both the *flat_networks* property and
   the *network_vlan_ranges* property are optional. However, at least one of
   these properties must be specified. You can define a FLAT network with the
   *flat_networks* property, or you can define a VLAN aware network with the
   *network_vlan_ranges* property, or you can define both types of networks.
 - The *vlan_min:vlan_max* range is optional. If not specified, the vswitch
   will be VLAN UNAWARE and the networks created on the vswitch will work as
   flat networks, though they will be shown as VLAN networks in neutron. This
   is compatible with old configurations, but it is highly recommended that you
   specify all VLAN UNAWARE vswitches in *flat_networks* and all VLAN AWARE
   vswitches in *network_vlan_ranges*.

tenant_network_types
^^^^^^^^^^^^^^^^^^^^
 **Optional**

 **Section:** ml2

 **Value:** Ordered list of network types to allocate as tenant (project)
 networks, separated by commas. z/VM supports local, flat, and vlan.

 **Notes:**

 - The default value is "local".
 - It is recommended that you specify all z/VM-supported network types in
   the *tenant_network_types* property.
 - When you create a network with the neutron command, the network type is
   determined by the following, in this order:

    1. The value of the *--provider-network-type* parameter specified on
    the neutron command.
    
    2. The value of the *tenant_network_types* property in the neutron 
    configuration file.
    
    3. The default value "local".

type_drivers
^^^^^^^^^^^^
 **Optional**

 **Section:** ml2

 **Value:** Ordered list of network types to allocate as tenant (project)
 networks, separated by commas. z/VM supports local, flat, and vlan.

 **Notes:**

 - The default value is: "local,flat,vlan"
 - It is recommended that you specify all z/VM-supported types. Optionally,
   you can specify only those network types you intend to support.

In file /etc/neutron/plugins/zvm/neutron_zvm_plugin.ini
-------------------------------------------------------

cloud_connector_url
^^^^^^^^^^^^^^^^^^^
 **Required**

 **Section:** AGENT

 **Value:** URL to be used to communicate with z/VM cloud connector.

polling_interval
^^^^^^^^^^^^^^^^
 **Optional**

 **Section:** AGENT

 **Value:** Integer - agent polling interval specified in number of seconds.

 **Notes:** This value depends on the network and workload. The default value
 is 2.

rdev_list
^^^^^^^^^
 **Optional**

 **Section:** vswitch_name

 **Value:** The RDEV address of the OSA cards which are connected to the vswitch.

 **Notes:**

 - Only one RDEV address may be specified per vswitch. You should choose an
   active RDEV address.
 - The section name (for example, vsw2) is the name of the vswitch. 


zvm_cloud_connector_ca_file
^^^^^^^^^^^^^^^^^^^^^^^^^^^
 **Optional**

 **Section:** AGENT

 **Value:** CA certificate file to be verified in httpd server. It must be a
 path to a CA bundle to use.


zvm_cloud_connector_token_file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 **Optional**

 **Section:** AGENT

 **Value:** Token file that contains admin-token to access z/VM cloud connector
 http server.

 