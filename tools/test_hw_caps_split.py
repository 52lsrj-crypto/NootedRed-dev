"""校验 Vega10 与 GFX9 的硬件能力初始化分别路由，避免跳过 Vega10 setup。"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'NootedRed/X5000.cpp').read_text()


def main():
    assert 'orgSetupAndInitializeHWCapabilities' in SOURCE, '缺少 Vega10 org 字段'
    assert 'orgGFX9SetupAndInitializeHWCapabilities' in SOURCE, '缺少 GFX9 org 字段'

    assert '__ZN32AMDRadeonX5000_AMDVega10Hardware32setupAndInitializeHWCapabilitiesEv' in SOURCE
    assert '__ZN30AMDRadeonX5000_AMDGFX9Hardware32setupAndInitializeHWCapabilitiesEv' in SOURCE
    assert 'wrapGFX9SetupAndInitializeHWCapabilities' in SOURCE

    vega = re.search(r'void X5000::wrapSetupAndInitializeHWCapabilities\(.*?\n\}', SOURCE, re.S)
    assert vega, '未找到 Vega10 wrapper'
    assert 'orgSetupAndInitializeHWCapabilities' in vega.group(0), 'Vega10 wrapper 未调用 Vega10 org'
    assert 'orgGFX9SetupAndInitializeHWCapabilities' not in vega.group(0), 'Vega10 wrapper 不应调用 GFX9 org'

    gfx9 = re.search(r'void X5000::wrapGFX9SetupAndInitializeHWCapabilities\(.*?\n\}', SOURCE, re.S)
    assert gfx9, '未找到 GFX9 wrapper'
    assert 'orgGFX9SetupAndInitializeHWCapabilities' in gfx9.group(0), 'GFX9 wrapper 未调用 GFX9 org'

    print('PASS Vega10 and GFX9 hardware-capability setup are routed separately')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as error:
        print(f'FAIL {error}')
        sys.exit(1)