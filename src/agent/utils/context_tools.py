
import logging
from typing import Any, List

from langchain_core.messages import HumanMessage, ToolMessage, BaseMessage
logger = logging.getLogger(__name__)
# --- 辅助函数：深度清理上下文中的巨大图片数据 ---
def clear_image_data(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    强制截断所有超长字符串，并将历史图片转为占位符。
    """
    new_messages = []
    MAX_STR_LEN = 1000  # 超过此长度的文本通常是残留的 Base64

    for i, msg in enumerate(messages):
        is_last = (i == len(messages) - 1)
        
        # 处理用户消息
        if isinstance(msg, HumanMessage):
            if isinstance(msg.content, list):
                new_content = []
                for item in msg.content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        # 仅保留最后一条消息的真实图片
                        if is_last:
                            new_content.append(item)
                        else:
                            new_content.append({"type": "text", "text": "[历史图片占位符]"})
                    elif isinstance(item, dict) and item.get("type") == "text":
                        new_content.append(item)
                new_messages.append(HumanMessage(content=new_content, id=msg.id))
            else:
                # 文本长度超标则截断
                text = msg.content if len(msg.content) < MAX_STR_LEN else msg.content[:MAX_STR_LEN] + "..."
                new_messages.append(HumanMessage(content=text, id=msg.id))
        
        # 处理工具返回消息 (防止工具结果中带入 Base64)
        elif isinstance(msg, ToolMessage):
            content = msg.content if len(msg.content) < MAX_STR_LEN else msg.content[:MAX_STR_LEN] + " [数据过长已物理截断]"
            new_messages.append(ToolMessage(content=content, tool_call_id=msg.tool_call_id))
            
        else:
            new_messages.append(msg)
            
    return new_messages

def get_clean_query(messages: List[BaseMessage]) -> str:
    """提取最后两轮的纯文本用于记忆检索，避免嵌套字典污染 Embedding"""
    query_parts = []
    for m in messages[-10:]:
        if isinstance(m.content, str):
            query_parts.append(m.content)
        elif isinstance(m.content, list):
            texts = [i["text"] for i in m.content if isinstance(i, dict) and i.get("type") == "text"]
            query_parts.extend(texts)
    return " ".join(query_parts)