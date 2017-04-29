===================
Single Vlan Network
===================

Using the Default VLAN ID
-------------------------

This scenario uses a VLAN aware vswitch and its default (defined in z/VM) VLAN ID. You do not need
to configure any additional information in OpenStack related to the VLAN in the network. To OpenStack
the infrastructure appears the same as in the Flat network scenario. You can configure your vswitch name
to flat_network or network_vlan_ranges. You do not need to configure the VLAN ID for your network
in OpenStack as it appears to OpenStack as a "FLAT" network.

To use this scenario, the following configuration options are needed:
* Specify one of the following options in the neutron ML2 plugin configure file (default file name is /etc/neutron/plugins/ml2/ml2_conf.ini)::

    flat_networks = xcatvsw3
    network_vlan_ranges = xcatvsw3:1:4094

.. note::
    "xcatvsw3" is an example of a value used by the XCAT Management Network, so you should
    create this as a VLAN aware Layer 2 vswitch with a default VLAN ID defined on z/VM.
    
* In the neutron z/VM agent configure file (default file name is /etc/neutron/plugins/zvm/neutron_zvm_plugin.ini), the following options are needed::

    [AGENT]
    zvm_xcat_username = mnadmin
    zvm_xcat_password = admin
    zvm_xcat_server = 1.2.3.4
    xcat_zhcp_nodename = zhcp

.. note::
    The neutron z/VM agent configuration shown above is for ZVMa. Update the xcat_zhcp_nodename
    option in the neutron z/VM agent configuration file for ZVMb (default file name is 
    /etc/neutron/plugins/zvm/neutron_zvm_plugin.ini) to configure the neutron z/VM agent for ZVMb.


Using the User-Specified VLAN ID
--------------------------------

This scenario uses a VLAN aware SWITCH with the VLAN ID specified in OpenStack instead of using
the defined default VLAN ID specified for the vswitch in z/VM. The difference between this scenario
and  ``Using the Default VLAN ID`` above is that here the OpenStack user must specify
a VLAN ID for the instances to be deployed.

To use this scenario, the following configuration options are needed:

* In the neutron ML2 plugin configuration file (default file name is /etc/neutron/plugins/ml2/ml2_conf.ini), make sure that the network_vlan_ranges property is specified as follows::

    network_vlan_ranges = xcatvsw3:1:4094

.. note::
    xcatvsw3 is used by the XCAT Management Network. It should be a VLAN aware Layer 2 vswitch on z/VM.

* In the neutron z/VM agent configuration file (default file name is /etc/neutron/plugins/zvm/neutron_zvm_plugin.ini), the following options are needed::
    [AGENT]
    zvm_xcat_username = mnadmin
    zvm_xcat_password = admin
    zvm_xcat_server = 1.2.3.4
    xcat_zhcp_nodename = zhcp

.. note::
    The neutron z/VM agent configuration shown above is for ZVMa. Update the
    xcat_zhcp_nodename option in the neutron z/VM agent configuration file for ZVMb (default file name
    is /etc/neutron/plugins/zvm/neutron_zvm_plugin.ini) to configure the neutron z/VM agent for ZVMb.


After restarting the neutron server and neutron z/VM agent, follow these steps on the OpenStack
controller to create the network and subnet for each of the physical networks.

* Create the xCAT management network. Enter the following command::

    neutron net-create --shared xcat_mgt --provider:network_type vlan --provider:physical_network xcatvsw3
    --provider:segmentation_id 521

.. note::
   The segmentation_id is the VLAN ID. It should be in the range of network_vlan_ranges in
   /etc/neutron/plugins/ml2/ml2_conf.ini.

* Create the appropriate subnet for the xCAT management network, changing the IP range to the appropriate values according to the xCAT configuration::

   neutron subnet-create --allocation-pool start=1.2.3.5,end=1.2.4.254 --gateway 1.2.3.1 xcat_mgt 1.2.0.0/16

When new instances are spawned, neutron-zvm-agent will set the VLAN ID(521) for each instance. xCAT
MN can reach and manage the new instances through the management network.
