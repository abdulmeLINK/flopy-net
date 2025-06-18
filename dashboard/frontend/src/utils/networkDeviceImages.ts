/**
 * Network Device Image Assets
 * 
 * This module provides utilities for managing network device images in the topology visualization.
 * It maps service types to their corresponding SVG image files and provides helper functions
 * for loading and displaying network device icons.
 */

// Base path for network device images
const NETWORK_DEVICES_PATH = '/images/network-devices';

// Mapping of service types to their image files
export const NETWORK_DEVICE_IMAGES: { [key: string]: string } = {
  // FLOPY-NET Core Components
  'policy-engine': `${NETWORK_DEVICES_PATH}/asa.svg`,               // Policy Engine = Cisco ASA
  'fl-server': `${NETWORK_DEVICES_PATH}/fl_server.svg`,             // FL Server = Custom FL Server
  'fl-client': `${NETWORK_DEVICES_PATH}/docker_guest.svg`,          // FL Client = Docker Guest
  'sdn-controller': `${NETWORK_DEVICES_PATH}/multilayer_switch.svg`, // SDN Controller = Multilayer Switch
  'collector': `${NETWORK_DEVICES_PATH}/vbox_guest.svg`,            // Collector = VirtualBox Guest
  'cloud services': `${NETWORK_DEVICES_PATH}/cloud.svg`,           // Cloud Services = Cloud
  
  // Network Infrastructure
  'openvswitch': `${NETWORK_DEVICES_PATH}/ethernet_switch.svg`,     // Open vSwitch = Ethernet Switch
  'switch': `${NETWORK_DEVICES_PATH}/ethernet_switch.svg`,          // Switch = Ethernet Switch
  'multilayer_switch': `${NETWORK_DEVICES_PATH}/multilayer_switch.svg`,
  'router': `${NETWORK_DEVICES_PATH}/router.svg`,                   // Router = Router
  'hub': `${NETWORK_DEVICES_PATH}/hub.svg`,                         // Hub = Hub
  
  // Virtualization & Guests
  'host': `${NETWORK_DEVICES_PATH}/computer.svg`,                   // Host = Computer
  'server': `${NETWORK_DEVICES_PATH}/computer.svg`,                 // Server = Computer
  'docker_guest': `${NETWORK_DEVICES_PATH}/docker_guest.svg`,       // Docker = Docker Guest
  'qemu_guest': `${NETWORK_DEVICES_PATH}/qemu_guest.svg`,          // QEMU = QEMU Guest
  'vbox_guest': `${NETWORK_DEVICES_PATH}/vbox_guest.svg`,          // VirtualBox = VBox Guest
  'vmware_guest': `${NETWORK_DEVICES_PATH}/vmware_guest.svg`,      // VMware = VMware Guest
  'vpcs_guest': `${NETWORK_DEVICES_PATH}/vpcs_guest.svg`,          // VPCS = VPCS Guest
  
  // Network Services & Special Devices
  'firewall': `${NETWORK_DEVICES_PATH}/firewall.svg`,               // Firewall = Firewall
  'nat': `${NETWORK_DEVICES_PATH}/nat.svg`,                         // NAT = NAT
  'cloud': `${NETWORK_DEVICES_PATH}/cloud.svg`,                     // Cloud = Cloud
  'frame_relay_switch': `${NETWORK_DEVICES_PATH}/frame_relay_switch.svg`,
  'atm_switch': `${NETWORK_DEVICES_PATH}/atm_switch.svg`,
  'asa': `${NETWORK_DEVICES_PATH}/asa.svg`,                         // Cisco ASA
};

// Fallback image for unknown service types
export const DEFAULT_DEVICE_IMAGE = `${NETWORK_DEVICES_PATH}/computer.svg`;

/**
 * Get the image path for a specific service type
 * @param serviceType - The service type (e.g., 'policy-engine', 'fl-server')
 * @returns The image path for the service type or default if not found
 */
export const getDeviceImage = (serviceType: string): string => {
  return NETWORK_DEVICE_IMAGES[serviceType] || DEFAULT_DEVICE_IMAGE;
};

/**
 * Get all available device types
 * @returns Array of all available service types
 */
export const getAvailableDeviceTypes = (): string[] => {
  return Object.keys(NETWORK_DEVICE_IMAGES);
};

/**
 * Check if a service type has a corresponding image
 * @param serviceType - The service type to check
 * @returns True if image exists, false otherwise
 */
export const hasDeviceImage = (serviceType: string): boolean => {
  return serviceType in NETWORK_DEVICE_IMAGES;
};

/**
 * Device display names for UI
 */
export const DEVICE_DISPLAY_NAMES: { [key: string]: string } = {
  // FLOPY-NET Core Components
  'policy-engine': 'Policy Engine',
  'fl-server': 'FL Server',
  'fl-client': 'FL Client',
  'sdn-controller': 'SDN Controller',
  'collector': 'Collector',
  
  // Network Infrastructure
  'openvswitch': 'Open vSwitch',
  'switch': 'Switch',
  'multilayer_switch': 'Multilayer Switch',
  'router': 'Router',
  'hub': 'Hub',
  
  // Virtualization & Guests
  'host': 'Host',
  'server': 'Server',
  'docker_guest': 'Docker Container',
  'qemu_guest': 'QEMU VM',
  'vbox_guest': 'VirtualBox VM',
  'vmware_guest': 'VMware VM',
  'vpcs_guest': 'VPCS',
  
  // Network Services & Special Devices
  'firewall': 'Firewall',
  'nat': 'NAT',
  'cloud': 'Cloud',
  'frame_relay_switch': 'Frame Relay Switch',
  'atm_switch': 'ATM Switch',
  'asa': 'Cisco ASA',
};

/**
 * Get the display name for a service type
 * @param serviceType - The service type
 * @returns The human-readable display name
 */
export const getDeviceDisplayName = (serviceType: string): string => {
  return DEVICE_DISPLAY_NAMES[serviceType] || serviceType.charAt(0).toUpperCase() + serviceType.slice(1);
};

/**
 * Network device categories for organization
 */
export const DEVICE_CATEGORIES = {
  'fl-components': ['policy-engine', 'fl-server', 'fl-client', 'collector'],
  'network-infrastructure': ['sdn-controller', 'openvswitch', 'switch', 'multilayer_switch', 'router', 'hub'],
  'virtualization': ['docker_guest', 'qemu_guest', 'vbox_guest', 'vmware_guest', 'vpcs_guest'],
  'security': ['firewall', 'asa'],
  'endpoints': ['host', 'server', 'computer'],
  'services': ['nat', 'cloud', 'frame_relay_switch', 'atm_switch'],
} as const;

/**
 * Get the category of a device type
 * @param serviceType - The service type
 * @returns The category name or 'other' if not categorized
 */
export const getDeviceCategory = (serviceType: string): string => {
  for (const [category, devices] of Object.entries(DEVICE_CATEGORIES)) {
    if ((devices as readonly string[]).includes(serviceType)) {
      return category;
    }
  }
  return 'other';
};
