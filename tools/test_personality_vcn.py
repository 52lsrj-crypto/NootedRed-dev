"""校验 IOKit personality 的设备覆盖与视频能力声明。

Raven/Picasso 是 VCN1，当前未接入 VCN2 桥接；如果 personality 继续声明
AMDVCN2/HEVC，VideoToolbox 会误判硬解能力，因此这里把 XML 与
VCNCapabilities.hpp 的代际表做交叉校验。
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PERSONALITIES = ROOT / 'NootedRed/Personalities'
VCN1 = {0x15D8, 0x15DD}
VCN22 = {0x15E7, 0x1636, 0x1638, 0x164C}


def load_dicts(path):
    root = ET.parse(path).getroot()
    assert root.tag == 'array', f'{path.name}: 顶层应为 array'
    return root.findall('dict')


def top_value(node, key):
    children = list(node)
    for i in range(0, len(children) - 1, 2):
        if children[i].tag == 'key' and children[i].text == key:
            return children[i + 1]
    return None


def text_value(node, key):
    value = top_value(node, key)
    if value is None or value.tag not in ('string', 'integer'):
        return None
    return value.text


def pci_devices(dicts):
    result = set()
    for node in dicts:
        match = text_value(node, 'IOPCIMatch')
        if not match:
            continue
        for token in match.split():
            if not re.fullmatch(r'0x[0-9A-Fa-f]{4}1002', token):
                raise AssertionError(f'IOPCIMatch 格式不正确：{token}')
            result.add(int(token[:6], 16))
    return result


def check_x5000():
    path = PERSONALITIES / 'com.apple.kext.AMDRadeonX5000.xml'
    dicts = load_dicts(path)

    for node in dicts:
        match = text_value(node, 'IOPCIMatch')
        if not match:
            continue
        devices = {int(token[:6], 16) for token in match.split()}
        vcn1 = devices & VCN1
        vcn22 = devices & VCN22
        if vcn1:
            for key in ('IODVDBundleName', 'IOGVACodec', 'IOGVAH264EncodeCapabilities',
                        'IOGVAHEVCDecode', 'IOGVAHEVCDecodeCapabilities',
                        'IOGVAHEVCEncode', 'IOGVAHEVCEncodeCapabilities'):
                assert text_value(node, key) is None and top_value(node, key) is None, \
                    f'VCN1 设备 {sorted(hex(d) for d in vcn1)} 不应声明 {key}'
        if vcn22:
            assert text_value(node, 'IOGVACodec') == 'AMDVCN2', \
                f'VCN2.2 设备 {sorted(hex(d) for d in vcn22)} 缺少 AMDVCN2'
            assert text_value(node, 'IOGVAHEVCDecode') == '1', 'VCN2.2 缺少 HEVC decode'
            assert text_value(node, 'IOGVAHEVCEncode') in ('1', '2'), 'VCN2.2 缺少 HEVC encode'

    assert pci_devices(dicts) == VCN1 | VCN22, 'X5000 personality 未覆盖全部 APU DID'

    # 与 VCNCapabilities.hpp 的代际表交叉校验
    source = (ROOT / 'NootedRed/VCNCapabilities.hpp').read_text()
    table = re.findall(r'\{\s*(0x[0-9A-Fa-f]{4})\s*,\s*Generation::(VCN1|VCN22)\s*,', source)
    assert table, '未找到 VCNCapabilities 设备表'
    code_vcn1 = {int(did, 16) for did, gen in table if gen == 'VCN1'}
    code_vcn22 = {int(did, 16) for did, gen in table if gen == 'VCN22'}
    assert code_vcn1 == VCN1, f'VCNCapabilities VCN1 集合不一致：{code_vcn1}'
    assert code_vcn22 == VCN22, f'VCNCapabilities VCN2.2 集合不一致：{code_vcn22}'
    print(f'PASS X5000 personality: VCN1={sorted(hex(d) for d in VCN1)} 无 VCN2 声明; '
          f'VCN2.2={sorted(hex(d) for d in VCN22)}')


def check_framebuffer_and_hda():
    fb = PERSONALITIES / 'com.apple.kext.AMDRadeonX6000Framebuffer.xml'
    fb_devices = pci_devices(load_dicts(fb))
    assert VCN1 | VCN22 <= fb_devices, f'X6000FB personality 未覆盖全部 APU DID：{fb_devices}'

    hw = PERSONALITIES / 'com.apple.kext.AMDRadeonX5000HWServices.xml'
    hw_devices = pci_devices(load_dicts(hw))
    assert VCN1 | VCN22 <= hw_devices, f'HWServices personality 未覆盖全部 APU DID：{hw_devices}'

    hda = PERSONALITIES / 'com.apple.driver.AppleGFXHDA.xml'
    hda_devices = pci_devices(load_dicts(hda))
    assert {0x15DE, 0x1637} <= hda_devices, f'AppleGFXHDA 未覆盖 Raven/Renoir HDAU：{hda_devices}'
    print('PASS X6000FB/HWServices/AppleGFXHDA 设备覆盖')


def main():
    check_x5000()
    check_framebuffer_and_hda()
    print('PASS personality VCN capability matrix')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as error:
        print(f'FAIL {error}')
        sys.exit(1)