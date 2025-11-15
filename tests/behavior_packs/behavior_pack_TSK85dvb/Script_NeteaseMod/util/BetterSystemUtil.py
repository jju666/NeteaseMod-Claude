# -*- coding: utf-8 -*-
"""
BetterSystemUtil - 系统工具类

提供文本格式化、颜色代码转换等实用功能
对应老项目的 BetterPartUtil

原文件: Parts/GamingState/util/BetterPartUtil.py
重构为: util/BetterSystemUtil.py
"""


class BetterSystemUtil(object):
    """系统工具类 - 提供文本格式化等实用功能"""

    # Minecraft颜色代码映射表
    # 参考: https://minecraft.fandom.com/zh/wiki/%E6%A0%BC%E5%BC%8F%E5%8C%96%E4%BB%A3%E7%A0%81
    # 注意: 必须使用u前缀以确保在Python 2中正确解释Unicode转义序列
    COLOR_CODES = {
        "enter": "\n",                      # 换行
        "black": u"\u00A70",                # 黑色
        "dark-blue": u"\u00A71",            # 深蓝
        "dark-green": u"\u00A72",           # 深绿
        "dark-aqua": u"\u00A73",            # 深青绿
        "dark-red": u"\u00A74",             # 深红
        "dark-purple": u"\u00A75",          # 深紫
        "gold": u"\u00A76",                 # 金色
        "gray": u"\u00A77",                 # 灰色
        "dark-gray": u"\u00A78",            # 深灰色
        "blue": u"\u00A79",                 # 蓝色
        "green": u"\u00A7a",                # 绿色
        "aqua": u"\u00A7b",                 # 青绿
        "red": u"\u00A7c",                  # 红色
        "light-purple": u"\u00A7d",         # 亮紫
        "yellow": u"\u00A7e",               # 黄色
        "white": u"\u00A7f",                # 白色
        "bold": u"\u00A7l",                 # 粗体
        "italic": u"\u00A7o",               # 斜体
        "reset": u"\u00A7r",                # 重置格式
    }

    @staticmethod
    def format_text(template, **kwargs):
        """
        格式化文本 - 替换颜色标记和变量

        Args:
            template (str/unicode): 模板文本，包含 {color} 标记和 {var} 变量
            **kwargs: 变量字典，用于替换 {var}

        Returns:
            str: 格式化后的UTF-8字节串（Python 2.7的str类型）

        示例:
            >>> BetterSystemUtil.format_text(
            ...     u'我拥有 {yellow}起床战争硬币: {coin}',
            ...     coin=999
            ... )
            '我拥有 \\xc2\\xa7e起床战争硬币: 999'

        注意:
            - 颜色标记（如 {yellow}）会被替换为 Minecraft 颜色代码
            - 变量（如 {coin}）会被替换为 kwargs 中的对应值
            - 返回UTF-8编码的字节串，与老项目BetterPartUtil保持一致
        """
        try:
            # 确保template是str类型（UTF-8字节串）
            if isinstance(template, unicode):
                template = template.encode('utf-8')

            # 步骤1: 替换颜色标记 {color} -> UTF-8编码的颜色代码
            for key, value in BetterSystemUtil.COLOR_CODES.items():
                # 将Unicode颜色代码转换为UTF-8字节串
                if isinstance(value, unicode):
                    value = value.encode('utf-8')

                # 替换 {key} -> value
                key_pattern = '{' + key + '}'
                if isinstance(key_pattern, unicode):
                    key_pattern = key_pattern.encode('utf-8')

                template = template.replace(key_pattern, value)

            # 步骤2: 替换变量 {var} -> value
            for key, value in kwargs.items():
                # 转换value为UTF-8字节串
                if isinstance(value, unicode):
                    value = value.encode('utf-8')
                elif not isinstance(value, str):
                    value = str(value)

                # 替换 {key} -> value
                key_pattern = '{' + key + '}'
                if isinstance(key_pattern, unicode):
                    key_pattern = key_pattern.encode('utf-8')

                template = template.replace(key_pattern, value)

            return template

        except Exception as e:
            print("[ERROR] [BetterSystemUtil] format_text 失败: template={} error={}".format(
                repr(template), str(e)
            ))
            import traceback
            traceback.print_exc()
            # 失败时返回原文本
            if isinstance(template, unicode):
                return template.encode('utf-8')
            return template

    @staticmethod
    def format_coin(coin):
        """
        格式化硬币数量显示

        Args:
            coin (int): 硬币数量

        Returns:
            unicode: 格式化后的硬币显示文本

        示例:
            >>> BetterSystemUtil.format_coin(1234)
            u'1,234'
            >>> BetterSystemUtil.format_coin(999999)
            u'999,999'
        """
        try:
            # 添加千分位分隔符
            return u"{:,}".format(coin)
        except:
            return unicode(coin)

    @staticmethod
    def split_lines(text, max_length=40):
        """
        按长度分割文本为多行

        Args:
            text (unicode): 要分割的文本
            max_length (int): 每行最大长度

        Returns:
            list[unicode]: 分割后的文本行列表

        用途:
            用于 ServerForm.label() 的长文本自动换行
        """
        if not text:
            return []

        lines = []
        current_line = u""

        for char in text:
            current_line += char
            if len(current_line) >= max_length or char == u'\n':
                lines.append(current_line)
                current_line = u""

        if current_line:
            lines.append(current_line)

        return lines
