# 事实记录表
FACT_EVENT_TABLE=r"""
CREATE TABLE events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增数字主键
    event_time TEXT NOT NULL,                   -- 事件时间
    location TEXT NOT NULL,                     -- 地点
    people TEXT NOT NULL,                       -- 多个人物组合的字符串
    content TEXT,                               -- 事件内容
    pain_level INTEGER DEFAULT 0 CHECK(pain_level >= 0),  -- 痛苦程度（非负数）
    happiness_level INTEGER DEFAULT 0 CHECK(happiness_level >= 0), -- 快乐程度（非负数）
);
"""

SIMPLE_FACT_EVENT_TABLE=r"""
CREATE TABLE IF NOT EXISTS events
(vector_id INTEGER PRIMARY KEY,
data TEXT)
"""