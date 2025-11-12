# -*- coding: utf-8 -*-
"""
添加自定义天气系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 自定义天气系统完整代码(精简版)
WEATHER_SYSTEM_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class WeatherServerSystem(ServerSystem):
    """自定义天气系统"""

    def __init__(self, namespace, systemName):
        super(WeatherServerSystem, self).__init__(namespace, systemName)

        # 天气配置
        self.weather_types = {
            "clear": {"rain": 0, "thunder": 0},
            "rain": {"rain": 1, "thunder": 0},
            "thunder": {"rain": 1, "thunder": 1}
        }

        self.current_weather = "clear"
        self.weather_duration = 0

        self.weather_comp = None
        self.Create()

    def Create(self):
        """初始化组件"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.weather_comp = comp_factory.CreateWeather(level_id)

    def SetWeather(self, weather_type, duration=6000):
        """设置天气"""
        if weather_type not in self.weather_types:
            print("[Weather] 未知天气类型: {}".format(weather_type))
            return False

        config = self.weather_types[weather_type]

        # 设置降雨
        self.weather_comp.SetRainLevel(config["rain"])
        # 设置雷暴
        self.weather_comp.SetThunderLevel(config["thunder"])

        self.current_weather = weather_type
        self.weather_duration = duration

        print("[Weather] 天气已设置为: {} 持续: {}tick".format(weather_type, duration))
        return True

    def GetCurrentWeather(self):
        """获取当前天气"""
        return self.current_weather

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 自定义天气系统玩法包配置
WEATHER_SYSTEM_PACK = {
    "id": "weather-system",
    "name": "自定义天气系统",
    "keywords": [
        "天气", "雨", "雷暴", "晴天", "气候", "降雨",
        "weather", "rain", "thunder", "clear", "climate", "storm"
    ],
    "category": "世界玩法",
    "difficulty": "简单",
    "estimated_time": "8分钟",

    "description": "实现自定义天气系统,支持设置晴天、雨天、雷暴等天气类型及持续时间",

    "implementation_guide": {
        "principle": "使用weatherComp.SetRainLevel和SetThunderLevel设置降雨和雷暴等级",

        "modsdk_apis": [
            {
                "name": "weatherComp.SetRainLevel",
                "type": "组件方法",
                "purpose": "设置降雨等级",
                "params": {
                    "rainLevel": "降雨等级 (float,0-1)"
                },
                "doc_path": "MODSDK/Component/weatherComp.md",
                "common_pitfall": "值范围为0-1,0表示无雨,1表示最大降雨"
            },
            {
                "name": "weatherComp.SetThunderLevel",
                "type": "组件方法",
                "purpose": "设置雷暴等级",
                "params": {
                    "thunderLevel": "雷暴等级 (float,0-1)"
                },
                "doc_path": "MODSDK/Component/weatherComp.md",
                "common_pitfall": "需先设置rain>0才能看到雷暴效果"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/WeatherServerSystem.py",
            "content": WEATHER_SYSTEM_CODE
        },

        "config_guide": {
            "description": "在weather_types中配置天气类型",
            "example": {
                "heavy_rain": {"rain": 1.0, "thunder": 0},
                "light_rain": {"rain": 0.3, "thunder": 0}
            },
            "fields": {
                "rain": "降雨等级 (float,0-1)",
                "thunder": "雷暴等级 (float,0-1)"
            }
        },

        "common_issues": [
            {
                "problem": "雷暴不显示",
                "cause": "rain等级为0",
                "solution": "确保rain>0时才设置thunder"
            },
            {
                "problem": "天气变化不平滑",
                "cause": "等级直接设置为目标值",
                "solution": "可以逐步递增/递减等级实现渐变"
            }
        ],

        "related_gameplay": [
            {
                "name": "粒子特效生成系统",
                "similarity": "视觉效果",
                "extension": "可扩展为天气效果增强"
            }
        ]
    }
}

def main():
    # 读取现有知识库
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    # 检查是否已存在
    existing_ids = [p["id"] for p in kb["gameplay_patterns"]]
    if "weather-system" in existing_ids:
        print("[SKIP] Weather System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(WEATHER_SYSTEM_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Weather System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(WEATHER_SYSTEM_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
