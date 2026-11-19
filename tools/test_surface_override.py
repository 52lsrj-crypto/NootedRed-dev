"""校验 getSurfaceInfo 覆盖默认关闭，getDisplayInfo 保留，仅 -NRedSurfaceOverride 启用 surface。"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'NootedRed/X5000.cpp').read_text()


def main():
    assert '-NRedSurfaceOverride' in SOURCE, '缺少 -NRedSurfaceOverride 开关'
    assert 'setProp32("NRedSurfaceOverride", 0)' in SOURCE, '缺少关闭状态属性'
    assert 'setProp32("NRedSurfaceOverride", 1)' in SOURCE, '缺少启用状态属性'

    main_requests = re.search(r'PatternRouteRequest requests\[\] = \{(.*?)\n    \};', SOURCE, re.S)
    assert main_requests, '未找到默认 requests 数组'
    assert 'getDisplayInfo' in main_requests.group(1), '默认应保留 getDisplayInfo'
    assert 'getSurfaceInfo' not in main_requests.group(1), '默认仍安装 getSurfaceInfo'

    surface_requests = re.search(r'PatternRouteRequest surfaceRequests\[\] = \{(.*?)\n    \};', SOURCE, re.S)
    assert surface_requests, '未找到 surfaceRequests 数组'
    assert 'getDisplayInfo' not in surface_requests.group(1), 'surfaceRequests 不应包含 getDisplayInfo'
    assert 'getSurfaceInfo' in surface_requests.group(1), 'surfaceRequests 缺少 getSurfaceInfo'

    gate = SOURCE[SOURCE.index('if (checkKernelArgument("-NRedSurfaceOverride"))'):]
    assert 'routeAll(patcher, id, surfaceRequests' in gate, '开关未控制 surfaceRequests 路由'

    assert 'ADDR2_COMPUTE_SURFACE_INFO_INPUT input{};' in SOURCE, 'getSurfaceInfo 输入未清零'
    assert SOURCE.count('ADDR2_COMPUTE_SURFACE_INFO_INPUT surfInfoInput{};') >= 2, '显示输入未清零'
    assert 'ADDR2_COMPUTE_SURFACE_INFO_OUTPUT surfInfoOutput{};' in SOURCE, '显示输出未清零'
    assert 'self->surfInfoOutputs()[fbIndex] = {};' in SOURCE, 'surface 输出未在调用前清零'

    print('PASS getDisplayInfo kept; getSurfaceInfo default-off and gated by -NRedSurfaceOverride; '
          'inputs/outputs zero-initialized')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as error:
        print(f'FAIL {error}')
        sys.exit(1)