#pragma once
#include <IOKit/IOTypes.h>

// 运行时解析失败诊断：记录最后一次失败的阶段码与各阶段累计次数。
// 只用于定位 CacheMismatch 的具体分支，不参与任何补丁语义。
namespace VPF
{
    enum ResolveFailStage : UInt32
    {
        FailImageForCache   = 1,   // imageForCache: 进程内镜像头不可读/路径不符
        FailSegmentOrSize   = 2,   // segmentCount > 8 或 fn.size < 32
        FailImageBounds     = 3,   // imageBounds 失败
        FailEntryRead       = 4,   // 候选地址 15 字节读不出来
        FailEntryBytes      = 5,   // matchBytes 前缀/函数体不匹配
        FailRefRead         = 6,   // 引用字段读不出 / relativeTarget 失败
        FailRefContains     = 7,   // 引用目标不在镜像内
        FailRefTarget       = 8,   // target() 解析失败
        FailRefMismatch     = 9,   // 引用目标与期望不符
        FailScan            = 10,  // scanFunction 未找到
        FailScratch         = 11,  // resolveScratch 失败
        FailResolveImages   = 12,  // resolveImages 失败
        FailDisplayImage    = 13,  // 显示路径 imageForCache 失败
        FailDisplayOther    = 14,  // 显示路径其它失败
        FailMax             = 15,
    };

    inline UInt32 lastFailStage{0};
    inline UInt32 failStageCounts[16]{};

    inline void markFail(const UInt32 stage)
    {
        __atomic_store_n(&lastFailStage, stage, __ATOMIC_RELAXED);
        __atomic_add_fetch(&failStageCounts[stage < 16 ? stage : 15], 1U, __ATOMIC_RELAXED);
    }
} // namespace VPF

namespace VPF
{
    // 提交路径首次 imageForCache 成功时的镜像/文本布局快照，供 ioreg 侧核对。
    inline UInt64 diagImgAddr{0}, diagTextAddr{0}, diagTextSize{0};
    inline UInt32 diagSegs{0}, diagFirst4{0}, diagFirst4Ok{0};
}
