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

Overview
********

System z is a family name used by IBM for all of its mainframe computers. IBM
System z are the direct descendants of System/360, announced in 1964, and the
System/370 from 1970s, and now includes the IBM System z9, the IBM System z10
and the newer IBM zEnterprise. System z is famous for its high availability and
used in government, financial services, retail, manufacturing, and just about
every other industry.

z/VM is a hypervisor for the IBM System z platform that provides a highly
flexible test and production environment. z/VM offers a base for customers who
want to exploit IBM virtualization technology on one of the industry's
best-of-breed server environments, the IBM System z family.

The z/VM cloud connector is a development sdk for manage z/VM. It provides a
set of APIs to operate z/VM including guest, image, network, volume etc. For
more info, please refer to `z/VM cloud connector`_.

.. _`z/VM cloud connector`: https://cloudlib4zvm.readthedocs.io/en/latest/

The neutron z/VM driver is designed as a neutron Layer 2 plugin/agent
combination, to enable OpenStack to exploit z Systems and z/VM virtual network
facilities through the z/VM cloud connector. Typically, from the OpenStack
neutron perspective, a neutron plugin performs the database related work,
while a neutron agent performs the real configuration work on hypervisors.
Note that in this document, the terms "neutron z/VM plugin" and
"neutron z/VM agent" both refer to the neutron z/VM driver.

The main component of the neutron z/VM driver is neutron-zvm-agent, which is
designed to work with a Neutron server running with the ML2 plugin. The neutron
z/VM driver uses the neutron ML2 plugin to do database related work, and
neutron-zvm-agent will use the z/VM cloud connector to do real network
configuration work on z/VM.


Notes:
 - One neutron-zvm-agent can work with or configure only one z/VM host.

 - The neutron z/VM driver does not support IPV6.

Note that there are some terminology differences between OpenStack and the
neutron z/VM driver, as follows:

+---------------------------+------------------------------------------+
| OpenStack                 | Neutron z/VM Driver                      |
+===========================+==========================================+
| Physical network          | z/VM vswitch                             |
+---------------------------+------------------------------------------+
| Segmentation ID           | VLAN ID                                  |
+---------------------------+------------------------------------------+
| FLAT                      | VLAN UNAWARE                             |
+---------------------------+------------------------------------------+
| base_mac                  | System prefix or user prefix             |
+---------------------------+------------------------------------------+

The neutron z/VM driver uses a z/VM vswitch to provide connectivity for
OpenStack instances. Refer to `z/VM: Connectivity`_ for more information on
vswitches and the z/VM network concept.

.. _`z/VM: Connectivity`: https://www.ibm.com/support/knowledgecenter/SSB27U_6.4.0/com.ibm.zvm.v640.hcpa6/toc.htm

Note that neutron z/VM driver only supports the z/VM vswitch with user based
and ETHERNET transport type.


